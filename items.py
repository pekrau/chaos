"Item class, subclasses and helper functions."

import contextlib
import copy
import datetime as dt
import functools
import mimetypes
import os
import pathlib
import re
import shutil
import sqlite3

import filetype
import yaml

import constants
import errors
import utils

# Lookup of item types.
TYPES = {}

# Global item lookup. Key: item id; value: item instance.
lookup = {}

# Global current state.
state = dict(pinned=[], recent=[])


class Item:
    "Abstract item class."

    def __init_subclass__(cls, **kwargs):
        global TYPES
        if not cls.__name__.startswith("_"):
            TYPES[cls.__name__.lower()] = cls

    def __init__(self, path=None):
        self._path = path
        self.frontmatter = dict(type=self.__class__.__name__.lower())
        self.text = ""
        self.refs_to_self = set()

    def __str__(self):
        return self.title

    def __repr__(self):
        return self.url

    def __hash__(self):
        return hash(self.id)

    @property
    def type(self):
        return self.frontmatter["type"]

    @property
    def id(self):
        return self.path.stem

    @property
    def path(self):
        return self._path

    @property
    def url(self):
        return f"/{self.type}/{self.id}"

    @property
    def title(self):
        try:
            return self.frontmatter["title"]
        except KeyError:
            return self.path.stem

    @title.setter
    def title(self, title):
        "Set the title. If the path has not been set, set it to a unique value."
        global lookup
        self.frontmatter["title"] = title.strip() or "no title"
        if self.path is None:
            self._path = constants.DATA_DIR / f"{get_id(utils.normalize(title))}.md"
            lookup[self.id] = self

    @property
    def size(self):
        "Size of the item Markdown file, in bytes."
        return self.path.stat().st_size

    @property
    def modified(self):
        "Modified timestamp in ISO format in UTC timezone."
        return utils.iso_utc_from_timestamp(self.path.stat().st_mtime)

    @property
    def modified_local(self):
        "Modified timestamp in ISO format in local timezone. Seconds not shown."
        return dt.datetime.fromtimestamp(
            self.path.stat().st_mtime, tz=constants.TIMEZONE
        ).strftime("%Y-%m-%d %H:%M")

    @property
    def age(self):
        "String representation of age; hh:mm:ss if less than 1 day, else days."
        age = dt.datetime.now() - dt.datetime.fromtimestamp(self.path.stat().st_mtime)
        hours, seconds = divmod(age.seconds, 3600)
        minutes, seconds = divmod(seconds, 60)
        if age.days > 0:
            return f"{age.days} d"
        else:
            return f"{hours}:{minutes:02d}:{seconds:02d}"

    @property
    def tag_ids(self):
        return self.frontmatter.get("tags", set())

    @property
    def tags(self):
        "Alphabetical list of tag items for the item."
        result = [get(id) for id in self.tag_ids]
        result.sort(key=lambda i: str(i).casefold())
        return result

    @tags.setter
    def tags(self, tags):
        """Set the tags for the item, which are items or their identifiers.
        No need to update '_tagged' elsewhere, since the 'write' will update it.
        """
        if tags:
            self.frontmatter["tags"] = set(
                [t.id if isinstance(t, Item) else t for t in tags]
            )
        else:
            self.frontmatter.pop("tags", None)

    @property
    def pinned(self):
        "Is this item pinned?"
        global state
        return self.id in state["pinned"]

    def similar(self):
        "Return a list of items similar to this. Currently based on tags."
        result = set()
        for tag in self.tags:
            result.update(tag.tagged)
        result.remove(self)
        tags = self.tag_ids
        return sorted(
            result,
            key=lambda i: (len(tags.intersection(i.tag_ids)), i.modified),
            reverse=True,
        )

    def write(self, refresh=True):
        """Write the item to file.
        Setup pointers between items again; inefficient, but defensive and safe.
        """
        with self.path.open(mode="w") as outfile:
            if self.frontmatter:
                frontmatter = copy.deepcopy(self.frontmatter)
                # Convert set to list for YAML output.
                try:
                    frontmatter["tags"] = list(frontmatter["tags"])
                except KeyError:
                    pass
                outfile.write("---\n")
                outfile.write(yaml.safe_dump(frontmatter, allow_unicode=True))
                outfile.write("---\n")
            if self.text:
                outfile.write(self.text)
        if refresh:
            setup_pointers()

    def delete(self):
        """Delete the item from the file system; move to trash.
        Remove from the lookup.
        Remove from pinned and recent, if present.
        Setup pointers between items again; inefficient, but defensive and safe.
        """
        global lookup, state
        shutil.move(self.path, constants.TRASH_DIR / self.id)
        lookup.pop(self.id)
        try:
            state["pinned"].remove(self.id)
        except ValueError:
            pass
        try:
            state["recent"].remove(self.id)
        except ValueError:
            pass
        write_state()
        setup_pointers()

    def score(self, term):
        """Calculate the score for the term in the title or text of the item.
        Presence in the title is weighted heavier.
        """
        rx = re.compile(f"{term.strip()}.*", re.IGNORECASE)
        return constants.SCORE_TITLE_WEIGHT * len(rx.findall(self.title)) + len(
            rx.findall(self.text)
        )

    @contextlib.contextmanager
    def patch(self):
        "Allow patching of the item leaving the MD file timestamp unchanged."
        stat = self.path.stat()
        utime = (stat.st_atime, stat.st_mtime)
        try:
            yield self
        finally:
            self.write(refresh=False)
            os.utime(self.path, times=utime)


class Note(Item):
    "Note item class."

    pass


class Tag(Item):
    "Tag item class."

    def __init__(self, path=None):
        super().__init__(path=path)
        self._tagged = set()  # Set of id's of items using this tag.

    @property
    def tagged(self):
        "List of tagged items."
        return [get(id) for id in self._tagged]


class Link(Item):
    "Link item class."

    @property
    def href(self):
        return self.frontmatter.get("href") or "/"

    @href.setter
    def href(self, href):
        self.frontmatter["href"] = href.strip() or "/"


@functools.total_ordering
class Event(Item):
    "Event item class; start and end datetimes."

    def __str__(self):
        return f"{self.title} ({self.display(date=True)})"

    def __lt__(self, other):
        assert isinstance(other, Event)
        return self.start < other.start or (
            self.start == other.start and self.end < other.end
        )

    def __eq__(self, other):
        if isinstance(other, Event):
            return self.start == other.start and self.end == other.end
        else:
            return False

    def __hash__(self):
        "It seems that this must be defined again, when '__eq__' is also defined?!"
        return hash(self.id)

    def __len__(self):
        "Duration in minutes."
        return round((self.end - self.start).total_seconds() / 60)

    @property
    def start(self):
        return self.frontmatter["start"]

    @start.setter
    def start(self, value):
        if isinstance(value, str):
            self.frontmatter["start"] = dt.datetime.fromisoformat(value)
        elif isinstance(value, dt.datetime):
            self.frontmatter["start"] = value
        else:
            raise ValueError("invalid datetime value")

    @property
    def end(self):
        return self.frontmatter["end"]

    @end.setter
    def end(self, value):
        if isinstance(value, str):
            self.frontmatter["end"] = dt.datetime.fromisoformat(value)
        elif isinstance(value, dt.datetime):
            self.frontmatter["end"] = value
        else:
            raise ValueError("invalid datetime value")

    @property
    def duration(self):
        "The duration of the event as a timedelta instance."
        return self.end - self.start

    @property
    def str_duration(self):
        "Formatted duration; weeks, days, hours, minutes."
        minutes = round(self.duration.total_seconds() / 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        weeks, days = divmod(days, 7)
        result = []
        if weeks:
            result.append(f"{weeks}w")
        if days:
            result.append(f"{days}d")
        if hours:
            result.append(f"{hours}h")
        if minutes:
            result.append(f"{minutes}m")
        return " ".join(result)

    def set(
        self, start_date, start_time, weeks, days, hours, minutes, end_date, end_time
    ):
        "Set the start and end from string values in ISO format and/or duration values."
        assert start_date
        if start_time:
            self.start = dt.datetime.combine(
                dt.date.fromisoformat(start_date), dt.time.fromisoformat(start_time)
            )
        else:
            self.start = dt.datetime.fromisoformat(start_date)
        # Duration; overrides any end datetime.
        if weeks or days or hours or minutes:
            self.end = self.start + dt.timedelta(
                weeks=weeks, days=days, hours=hours, minutes=minutes
            )
        # End date.
        elif end_date:
            # End time.
            if end_time and end_time != "00:00":
                self.end = dt.datetime.combine(
                    dt.date.fromisoformat(end_date), dt.time.fromisoformat(end_time)
                )
            # No end time; 1 day duration.
            else:
                end = dt.datetime.fromisoformat(end_date)
                if self.start.hour == 0 and self.start.minute == 0:
                    end = max(self.start, end) + dt.timedelta(days=1)
                self.end = end
        # Only end time; use start date.
        elif end_time:
            self.end = dt.datetime.combine(self.start, dt.time.fromisoformat(end_time))
        # No end datetime and no start time: 1 day duration.
        elif self.start.hour == 0 and self.start.minute == 0:
            self.end = self.start + dt.timedelta(days=1)
        # No end datetime and start time given: 1 hour duration.
        else:
            self.end = self.start + dt.timedelta(hours=1)

    @property
    def whole_days(self):
        "Does this event span a whole number of days?"
        return (
            self.start.hour == 0
            and self.start.minute == 0
            and self.duration.seconds == 0
        )

    @property
    def days(self):
        "Number of days this event affects; int."
        if self.whole_days:
            return self.end.toordinal() - self.start.toordinal()
        else:
            return self.end.toordinal() - self.start.toordinal() + 1

    @property
    def time(self):
        "The start time as formatted string."
        return self.start.strftime("%H:%M")

    @property
    def date(self):
        "The start date as formatted string."
        return self.start.strftime("%Y-%m-%d")

    @property
    def week(self):
        "The start week number."
        return self.start.isocalendar().week

    @property
    def weekday(self):
        "The start weekday name."
        return self.start.strftime("%A").capitalize()

    @property
    def weekday_short(self):
        "The start weekday abbreviated name."
        return self.start.strftime("%a").capitalize()

    @property
    def weekday_number(self):
        "The start weekday number."
        return self.start.isoweekday()

    @property
    def month(self):
        "The start month name."
        return self.start.strftime("%B")

    @property
    def month_short(self):
        "The start month abbreviated name."
        return self.start.strftime("%b")

    @property
    def _end(self):
        "The end datetime taking whole days into account."
        if self.whole_days:
            return self.end - dt.timedelta(days=1)
        else:
            return self.end

    @property
    def end_time(self):
        "The end time."
        return self.end.strftime("%H:%M")

    @property
    def end_week(self):
        "The end week number."
        return self._end.isocalendar().week

    @property
    def end_weekday(self):
        "The end weekday name."
        return self._end.strftime("%A").capitalize()

    @property
    def end_weekday_short(self):
        "The end weekday abbreviated name."
        return self._end.strftime("%a").capitalize()

    @property
    def end_weekday_number(self):
        "The end weekday number."
        return self._end.isoweekday()

    @property
    def end_day(self):
        "The end day month number."
        return self._end.day

    @property
    def end_month(self):
        "The end month name."
        return self._end.strftime("%B")

    @property
    def end_month_short(self):
        "The end month name abbreviation."
        return self._end.strftime("%b")

    @property
    def end_year(self):
        "The end year number."
        return self._end.year

    @property
    def category(self):
        return self.frontmatter.get("category", constants.EVENT_CATEGORIES[0])

    @category.setter
    def category(self, value):
        assert (not value) or (value in constants.EVENT_CATEGORIES)
        if value:
            self.frontmatter["category"] = value
        else:
            self.frontmatter.pop("category", None)

    def within(self, start, end):
        "Is this event within the given start and end datetimes?"
        assert isinstance(start, dt.datetime)
        assert isinstance(end, dt.datetime)
        return start <= self.start and self.end <= end

    def overlap(self, start, end):
        """Return the overlap in minutes of this event with the given start
        and end datetimes. Zero if no overlap.
        """
        assert isinstance(start, dt.datetime)
        assert isinstance(end, dt.datetime)
        if self.end <= start:
            return 0
        if self.start >= end:
            return 0
        if start <= self.start:
            if self.end <= end:
                return len(self)
            else:
                return round((end - self.start).total_seconds() / 60)
        elif self.end < end:
            return round((self.end - start).total_seconds() / 60)
        else:
            return round((end - start).total_seconds() / 60)

    def overlap_days(self, start, end):
        "Does this event overlap any of the days between 'start' and 'end'?"
        assert isinstance(start, dt.datetime)
        assert isinstance(end, dt.datetime)
        return not (
            self._end.toordinal() < start.toordinal()
            or self.start.toordinal() > end.toordinal()
        )

    def overlap_hours(self, start, end):
        "Does this event overlap any of the hours between 'start' and 'end'?"
        assert isinstance(start, dt.datetime)
        assert isinstance(end, dt.datetime)
        return not (
            (24 * self._end.toordinal() + self._end.hour)
            < (24 * start.toordinal() + start.hour)
            or (24 * self.start.toordinal() + self.start.hour)
            > (24 * end.toordinal() + end.hour)
        )

    def check(self):
        "Check that the current event value is valid, i.e. start <= end."
        if self.start > self.end:
            raise ValueError("invalid event; start must be <= end")

    def isodate(self, month=True, day=True, week=False):
        "Return formatted date in ISO style."
        if week:
            return f"{self.start.year}-{self.start.isocalendar().week}"
        elif day:
            return f"{self.start.year}-{self.start.month:02}-{self.start.day:02}"
        elif month:
            return f"{self.start.year}-{self.start.month:02}"
        else:
            return str(self.start.year)

    def display(self, date=False, year=None, time=True):
        """Human-readable representation of the period for the event.
        Omit date if less than one day.
        """
        if self.start.year == self.end_year:
            if self.month == self.end_month:
                if self.whole_days:
                    if self.days == 1:
                        if year and year == self.start.year:
                            return f"{self.start.day} {self.month}"
                        else:
                            return f"{self.start.day} {self.month} {self.start.year}"
                    elif year and year == self.start.year:
                        return f"{self.start.day}-{self.end_day} {self.month}"
                    else:
                        return f"{self.start.day}-{self.end_day} {self.month} {self.start.year}"
                elif self.start.day == self.end.day:
                    if date:
                        if year and year == self.start.year:
                            return f"{self.weekday} {self.start.day} {self.month} {self.time}-{self.end_time}"
                        else:
                            return f"{self.weekday} {self.start.day} {self.month} {self.start.year} {self.time}-{self.end_time}"
                    else:
                        return f"{self.time}-{self.end_time}"
                elif year and year == self.start.year:
                    return f"{self.start.day}-{self.end_day} {self.month}"
                else:
                    return f"{self.start.day}-{self.end_day} {self.month} {self.start.year}"
            # Different months; same year.
            elif year and year == self.start.year:
                return f"{self.start.day} {self.month_short} - {self.end_day} {self.end_month_short}"
            else:
                return f"{self.start.day} {self.month_short} - {self.end_day} {self.end_month_short}  {self.start.year}"
        else:  # Different years; ignore flag.
            return f"{self.start.day} {self.month_short} {self.start.year} - {self.end_day} {self.end_month_short} {self.end_year}"


class _GenericFile(Item):
    "Generic file item class."

    @property
    def ext(self):
        "The extension of the filename; signifies the MIME type."
        return self.frontmatter["ext"]

    @ext.setter
    def ext(self, value):
        self.frontmatter["ext"] = value

    @property
    def filename(self):
        return pathlib.Path(self.id + self.ext)

    @property
    def filepath(self):
        return constants.DATA_DIR / self.filename

    @property
    def file_size(self):
        "Size of the file, in bytes."
        return self.filepath.stat().st_size

    @property
    def mimetype(self):
        """Return MIME type, or None if not recognized.
        Determined primarily from the file data, from the file extension as fall-back.
        """
        kind = filetype.guess(self.filepath)  # Reads the file; needs absolute filename.
        if kind is None:
            return mimetypes.guess_type(self.filename)[0]  # Needs filename.
        # Sqlite3 special case; convert to the MIME type used in this package.
        elif kind.mime == "application/x-sqlite3":
            return constants.SQLITE_MIMETYPE
        else:
            return kind.mime

    @property
    def file_modified(self):
        "Modified timestamp in UTC ISO format."
        return utils.iso_utc_from_timestamp(self.filepath.stat().st_mtime)

    @property
    def url_file(self):
        "Return the URL for the file content."
        return self.url + self.ext

    def delete(self):
        "Delete the item and file from the file system and remove from the lookup."
        shutil.move(self.filepath, constants.TRASH_DIR / self.filename)
        super().delete()


class Image(_GenericFile):
    "Image item class."

    pass


class File(_GenericFile):
    "File item class."

    pass


class Database(_GenericFile):
    "Database (Sqlite3) item class."

    def connect(self, readonly=False):
        return _DatabaseConnection(self, readonly=readonly)

    def get_schema(self):
        "Return the definitions of tables and views in the database."
        result = {}
        with self.connect(readonly=True) as cnx:
            names = []
            for type in ["table", "view"]:
                sql = f"SELECT name FROM sqlite_schema WHERE type='{type}'"
                for (name,) in cnx.execute(sql):
                    if not name.startswith("_"):
                        names.append(name)
            for name in names:
                columns = {}
                for row in cnx.execute(f"pragma table_info({name})"):
                    columns[row[1]] = dict(
                        type=row[2],
                        null=not row[3],
                        default=row[4],
                        primary=bool(row[5]),
                    )
                relation = dict(columns=columns)
                sql = cnx.execute(
                    "SELECT sql FROM sqlite_schema WHERE name=?", (name,)
                ).fetchone()[0]
                relation["sql"] = sql
                relation["type"] = sql.split()[1].lower()
                relation["count"] = cnx.execute(
                    f"SELECT COUNT(*) FROM {name}"
                ).fetchone()[0]
                result[name] = relation
        return result

    @property
    def url_sql(self):
        "Return the URL to download the database as SQL."
        return f"{self.url}.sql"


class _DatabaseConnection:

    def __init__(self, database, readonly=False):
        self.database = database
        self.readonly = readonly

    def __enter__(self):
        if self.readonly:
            self.cnx = sqlite3.connect(
                f"file:{self.database.filepath}?mode=ro", uri=True
            )
        else:
            self.cnx = sqlite3.connect(self.database.filepath)
        return self.cnx

    def __exit__(self, etyp, einst, etb):
        if etyp is None:
            self.cnx.commit()
        else:
            self.cnx.rollback()
        self.cnx.close()


class Graphic(Item):
    "Graphic item class."

    @property
    def graphic(self):
        return self.frontmatter["graphic"]

    @property
    def specification(self):
        return self.frontmatter["specification"]


class _GenericReference(Item):
    "Generic book or article reference."

    @property
    def authors(self):
        "List of authors."
        return self.frontmatter["authors"]

    @authors.setter
    def authors(self, value):
        if isinstance(value, str):
            value = list(filter(None, [a.strip() for a in value.strip().split("\n")]))
        self.frontmatter["authors"] = value

    @property
    def published(self):
        "Publication date for this edition."
        return self.frontmatter.get("published")

    @published.setter
    def published(self, value):
        if isinstance(value, str):
            if value := value.strip():
                try:
                    value = dt.date.fromisoformat(value)
                except ValueError:  # Assume just year.
                    try:
                        value = dt.date(year=int(value), month=1, day=1)
                    except ValueError:
                        value = None
            else:
                value = None
        self.frontmatter["published"] = value

    @property
    def language(self):
        return self.frontmatter.get("language")

    @language.setter
    def language(self, value):
        if isinstance(value, str):
            value = value.strip() or None
        self.frontmatter["language"] = value


class Book(_GenericReference):
    "Reference to a book."

    @property
    def year(self):
        "Year first published."
        result = self.frontmatter.get("year")
        if not result and self.published:
            result = self.published.year
        return result

    @year.setter
    def year(self, value):
        if isinstance(value, str):
            if value := value.strip():
                value = int(value)
            else:
                value = None
        self.frontmatter["year"] = value

    @property
    def publisher(self):
        "Publisher for this edition."
        return self.frontmatter.get("publisher")

    @publisher.setter
    def publisher(self, value):
        if isinstance(value, str):
            value = value.strip() or None
        self.frontmatter["publisher"] = value

    @property
    def isbn(self):
        return self.frontmatter["isbn"]

    @isbn.setter
    def isbn(self, value):
        if isinstance(value, str):
            value = value.strip() or None
        self.frontmatter["isbn"] = value


class Article(_GenericReference):
    "Reference to an article."

    @property
    def journal(self):
        return self.frontmatter["journal"]

    @journal.setter
    def journal(self, value):
        if isinstance(value, str):
            value = value.strip() or None
        self.frontmatter["journal"] = value

    @property
    def volume(self):
        return self.frontmatter.get("volume")

    @volume.setter
    def volume(self, value):
        if isinstance(value, str):
            value = value.strip() or None
        self.frontmatter["volume"] = value

    @property
    def issue(self):
        return self.frontmatter.get("issue")

    @issue.setter
    def issue(self, value):
        if isinstance(value, str):
            value = value.strip() or None
        self.frontmatter["issue"] = value

    @property
    def pages(self):
        return self.frontmatter.get("pages")

    @pages.setter
    def pages(self, value):
        if isinstance(value, str):
            value = value.strip() or None
        self.frontmatter["pages"] = value

    @property
    def doi(self):
        return self.frontmatter["doi"]

    @doi.setter
    def doi(self, value):
        if isinstance(value, str):
            value = value.strip() or None
        self.frontmatter["doi"] = value

    @property
    def pmid(self):
        return self.frontmatter.get("pmid")

    @pmid.setter
    def pmid(self, value):
        if isinstance(value, str):
            value = value.strip() or None
        self.frontmatter["pmid"] = value


def get_id(stem):
    "Get a unique id given the stem; add suffix if necessary."
    global lookup
    result = stem
    n = 1
    while result in lookup:
        n += 1
        result = f"{stem}-{n}"
    return result


def get(itemid):
    "Get the item from the global lookup given its identifier."
    global lookup
    return lookup[itemid]


def write_state(recent=None, pin=None, unpin=None):
    global state
    if recent is not None:
        try:
            state["recent"].remove(recent.id)
        except ValueError:
            pass
        state["recent"].insert(0, recent.id)
    if pin is not None:
        if pin.id not in state["pinned"]:
            state["pinned"].append(pin.id)
    if unpin is not None:
        try:
            state["pinned"].remove(unpin.id)
        except ValueError:
            pass
    cleanup_state()
    while len(state["recent"]) > constants.MAX_RECENT_ITEMS + len(state["pinned"]) + 1:
        state["recent"].pop()
    constants.STATE_FILE.write_text(yaml.safe_dump(state, allow_unicode=True))


def get_shortcuts(item=None):
    """Get the pinned and recent items for display in the nav menu.
    If item is provided, update the recent items.
    """
    global lookup, state
    recent = list(state["recent"])
    if item is None:
        cleanup_state()
    else:
        try:
            recent.remove(item.id)
        except ValueError:
            pass
        write_state(recent=item)
    pinned = [id for id in state["pinned"]]
    recent = [id for id in recent if id not in pinned]
    return [get(id) for id in (pinned + recent)]


def cleanup_state():
    "Remove any non-existen ids from the state."
    global state
    state["recent"] = [id for id in state["recent"] if id in lookup]
    state["pinned"] = [id for id in state["pinned"] if id in lookup]


def read():
    """Read all items from Markdowwn files in the data directory.
    Create the data directory if it does not exist.
    Read the current state; recent and pinned items.
    Set up pointers between items.
    """
    global lookup, state
    try:
        state.clear()
        state.update(yaml.safe_load(constants.STATE_FILE.read_text()))
    except IOError:
        state = dict(pinned=[], recent=[])
        write_state()
    lookup.clear()
    for path in constants.DATA_DIR.iterdir():
        item = read_item(path)
        if item is not None:
            lookup[item.id] = item
    setup_pointers()


def read_item(path):
    "Read the Markdown file and return the item."
    if path.suffix != ".md":
        return None
    content = path.read_text()
    m = constants.FRONTMATTER.match(content)
    if not m:
        return None
    frontmatter = yaml.safe_load(m.group(1))
    # Convert tags from YAML list to set.
    try:
        frontmatter["tags"] = set(frontmatter["tags"])
    except KeyError:
        pass
    item = TYPES[frontmatter["type"]](path)
    item.frontmatter.update(frontmatter)
    item.text = content[m.start(2) :]
    return item


def patch_all_md_files():
    """Update the contents of all Markdown files to the current format.
    Should be able to handle any previous backup.
    """
    # Remove 'filename' and add 'ext' instead; for File, Image and Database items.
    for path in constants.DATA_DIR.iterdir():
        item = read_item(path)
        if item is None:
            continue
        if "filename" in item.frontmatter:
            with item.patch():
                filename = item.frontmatter.pop("filename")
                filename = pathlib.Path(filename)
                item.ext = filename.suffix
        # Remove timezone info from 'start' and 'end'; for Event items.
        if "start" in item.frontmatter:
            with item.patch():
                item.start = item.start.replace(tzinfo=None)
        if "end" in item.frontmatter:
            with item.patch():
                item.end = item.end.replace(tzinfo=None)


def setup_pointers():
    """For each tag item, record in '_tagged' those items using it.
    Set the 'refs_to_self' for item references."
    """
    for item in lookup.values():
        if isinstance(item, Tag):
            item._tagged.clear()
        item.refs_to_self.clear()
    for item in lookup.values():
        for tag in item.tags:
            tag._tagged.add(item.id)
        for m in constants.REF.finditer(item.text):
            try:
                other = get(m.group(1))
            except KeyError:
                pass
            else:
                other.refs_to_self.add(item.id)
        for m in constants.INCL.finditer(item.text):
            try:
                other = get(m.group(1))
            except KeyError:
                pass
            else:
                other.refs_to_self.add(item.id)


def get_items(type=None):
    "Get all items, or of a given type."
    global lookup
    if type is None:
        return lookup.values()
    else:
        type = type.lower()
        return (i for i in lookup.values() if i.type == type)


def get_all_files():
    "Get a map of item paths and filepaths with their 'modified' and 'size' values."
    global lookup
    result = {
        constants.STATE_FILE.name: utils.iso_utc_from_timestamp(
            constants.STATE_FILE.stat().st_mtime
        )
    }
    result = {}
    for item in lookup.values():
        result[item.id] = dict(modified=item.modified, size=item.size)
        if isinstance(item, (File, Image)):
            result[str(item.filename)] = dict(
                modified=item.file_modified, size=item.file_size
            )
    return result


def get_statistics():
    global TYPES
    result = dict(item=len(lookup))
    result.update(dict([(type, 0) for type in TYPES]))
    for item in lookup.values():
        result[item.type] += 1
    return result
