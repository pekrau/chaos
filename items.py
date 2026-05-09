"Item class, subclasses and helper functions."

import contextlib
import copy
import datetime as dt
import functools
import mimetypes
import os
import pathlib
import re
import sqlite3

import filetype
import yaml

import constants
import errors
import markdown
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
        self.frontmatter["title"] = title or "no title"
        if self.path is None:
            filename = utils.normalize(title)
            self._path = constants.DATA_DIR / f"{filename}.md"
            if self.id in lookup:
                n = 2
                while True:
                    self._path = constants.DATA_DIR / f"{filename}-{n}.md"
                    if self.id not in lookup:
                        break
                    n += 1
            lookup[self.id] = self

    @property
    def html(self):
        if self.text:
            return markdown.to_html(self.text)
        else:
            return None

    @property
    def size(self):
        "Size of the item Markdown file, in bytes."
        return self.path.stat().st_size

    @property
    def modified(self):
        "Modified timestamp in UTC ISO format."
        return utils.timestamp_utc(self.path.stat().st_mtime)

    @property
    def modified_local(self):
        "Modified timestamp in local ISO format."
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
            ic(tag, tag.tagged)
            result.update(tag.tagged)
        result.remove(self)
        tags = self.tag_ids
        return sorted(
            result,
            key=lambda i: (len(tags.intersection(i.tag_ids)), i.modified),
            reverse=True,
        )

    def write(self):
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
        setup_pointers()

    def delete(self):
        """Delete the item from the file system.
        Remove from the lookup.
        Remove from pinned and recent, if present.
        Setup pointers between items again; inefficient, but defensive and safe.
        """
        global lookup, state
        self.path.unlink()
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
        "Allow patching of the item leaving the file timestamps unchanged."
        stat = self.path.stat()
        utime = (stat.st_atime, stat.st_mtime)
        try:
            yield self
        finally:
            self.write()
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
    "Event item class; start and end datetimes in the local timezone."

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

    @property
    def start(self):
        return self.frontmatter["start"]

    @start.setter
    def start(self, value):
        if isinstance(value, str):
            self.frontmatter["start"] = dt.datetime.fromisoformat(value).replace(
                tzinfo=constants.TIMEZONE
            )
        elif isinstance(value, dt.datetime):
            self.frontmatter["start"] = value
        else:
            raise ValueError("invalid datetime value")

    def set_start(self, date, time):
        if time:
            self.frontmatter["start"] = dt.datetime.combine(
                dt.date.fromisoformat(date),
                dt.time.fromisoformat(time),
                tzinfo=constants.TIMEZONE,
            )
        else:
            self.frontmatter["start"] = dt.datetime.fromisoformat(date).replace(
                tzinfo=constants.TIMEZONE
            )

    @property
    def end(self):
        return self.frontmatter["end"]

    @end.setter
    def end(self, value):
        if isinstance(value, str):
            self.frontmatter["end"] = dt.datetime.fromisoformat(value).replace(
                tzinfo=constants.TIMEZONE
            )
        elif isinstance(value, dt.datetime):
            self.frontmatter["end"] = value
        else:
            raise ValueError("invalid datetime value")

    def set_end(self, date, time):
        if date:
            if time:
                self.frontmatter["end"] = dt.datetime.combine(
                    dt.date.fromisoformat(date),
                    dt.time.fromisoformat(time),
                    tzinfo=constants.TIMEZONE,
                )
            else:
                self.frontmatter["end"] = dt.datetime.fromisoformat(date).replace(
                    tzinfo=constants.TIMEZONE
                )
        elif time:
            self.frontmatter["end"] = dt.datetime.combine(
                self.start,
                dt.time.fromisoformat(time),
                tzinfo=constants.TIMEZONE,
            )
        elif self.start.hour == 0 and self.start.minute == 0:
            self.frontmatter["end"] = self.start + dt.timedelta(days=1)
        else:
            self.frontmatter["end"] = self.start + dt.timedelta(seconds=3600)

    @property
    def days(self):
        "Duration of event in days."
        return (self.end - self.start).total_seconds() / (24 * 3600)

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

    def after(self, datetime):
        "Is this event strictly after the given datetime?"
        assert isinstance(datetime, dt.datetime)
        return datetime <= self.start

    def before(self, datetime):
        "Is this event strictly before the given datetime?"
        assert isinstance(datetime, dt.datetime)
        return self.end <= datetime

    def precede(self, datetime):
        "Does this event directly precede the given datetime?"
        assert isinstance(datetime, dt.datetime)
        return datetime == self.start

    def follow(self, datetime):
        "Does this event directly follow the given datetime?"
        assert isinstance(datetime, dt.datetime)
        return self.end == datetime

    def within(self, start, end):
        "Is this event within the given start and end datetimes?"
        assert isinstance(start, dt.datetime)
        assert isinstance(end, dt.datetime)
        return start <= self.start and self.end <= end

    def overlap(self, start, end):
        "Does this event overlap with the given start and end datetimes?"
        assert isinstance(start, dt.datetime)
        assert isinstance(end, dt.datetime)
        return not (self.end <= start or end <= self.start)

    def check(self):
        "Check that the current event value is valid, i.e. start <= end."
        if self.start > self.end:
            raise ValueError("invalid event; start must be <= end")

    def nice(self, end=True, date=False, year=False, title=False):
        "Human-readable representation of the period of the event."
        result = []
        # Exactly one day: do not show times.
        if self.start + dt.timedelta(days=1) == self.end:
            if date:
                result.append(f"{utils.date(self.start)}")
            if year:
                result.append(str(self.start.year))
        # Less than one day: show period.
        elif self.end - self.start < dt.timedelta(days=1):
            if date:
                result.append(f"{utils.date(self.start, year=year)}")
                if end:
                    result.append(f"{utils.time(self.start)}-{utils.time(self.end)}")
                else:
                    result.append(f"{utils.time(self.start)}")
            elif end:
                result.append(f"{utils.time(self.start)}-{utils.time(self.end)}")
            else:
                result.append(f"{utils.time(self.start)}")
        # More than one day and 'end': show both dates.
        elif end:
            start_day = self.start.strftime("%d").lstrip("0")
            end_day = self.end.strftime("%d").lstrip("0")
            # Same year.
            if self.start.year == self.end.year:
                # Same month: show days interval.
                if self.start.month == self.end.month:
                    result.append(
                        f"{start_day} - {end_day} {self.start.strftime('%b')}"
                    )
                # Different month: show day and month interval.
                else:
                    result.append(
                        f"{start_day} {self.start.strftime('%b')} - {end_day} {self.end.strftime('%b')}"
                    )
                if year:
                    result.append(str(self.start.year))
            # Different years: year is shown regardless of argument.
            else:
                result.append(
                    f"{start_day} {self.start.strftime('%b %Y')} - {end_day} {self.end.strftime('%b %Y')}"
                )
        # Do not show end.
        else:
            result.append(
                f"{self.start.strftime('%d').lstrip('0')} {self.start.strftime('%b')}"
            )
            if year:
                result.append(str(self.start.year))
        if title:
            result.append(str(self))
        return " ".join(result)

    def nice_duration(self):
        minutes = round((self.end - self.start).total_seconds() / 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        if days:
            if hours == 0 and minutes == 0:
                return f"{days}d"
            else:
                return f"{days}d {hours:02}:{minutes:02}"
        else:
            return f"{hours:02}:{minutes:02}"


class _GenericFile(Item):
    "Generic file item class."

    @property
    def filename(self):
        return pathlib.Path(self.frontmatter["filename"])

    @filename.setter
    def filename(self, value):
        self.frontmatter["filename"] = filename

    @property
    def filepath(self):
        return constants.DATA_DIR / self.filename

    @property
    def file_size(self):
        "Size of the file, in bytes."
        return self.filepath.stat().st_size

    @property
    def ext(self):
        return self.filepath.suffix.lstrip(".")

    @property
    def file_mimetype(self):
        """Return MIME type, or None if not recognized.
        Determined from the file data, not from the file extension.
        """
        kind = filetype.guess(self.filepath)
        if kind is None:
            None
        # Special case; convert to the mimetype used in this package.
        elif kind.mime == "application/x-sqlite3":
            return constants.SQLITE_MIMETYPE
        else:
            return kind.mime

    @property
    def file_modified(self):
        "Modified timestamp in UTC ISO format."
        return utils.timestamp_utc(self.filepath.stat().st_mtime)

    @property
    def url_file(self):
        "Return the URL for the file content."
        return self.url + self.filename.suffix

    def delete(self):
        "Delete the item and file from the file system and remove from the lookup."
        self.filepath.unlink()
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
        return self.frontmatter["published"]

    @published.setter
    def published(self, value):
        if isinstance(value, str):
            if value := value.strip():
                try:
                    value = dt.date.fromisoformat(value)
                except ValueError:  # Assume just year.
                    pass
            else:
                value = None
        self.frontmatter["published"] = value

    @property
    def language(self):
        return self.frontmatter["language"]

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
    state["recent"] = [id for id in state["recent"] if id in lookup]
    state["pinned"] = [id for id in state["pinned"] if id in lookup]
    while len(state["recent"]) > constants.MAX_RECENT_ITEMS + len(state["pinned"]) + 1:
        state["recent"].pop()
    constants.STATE_FILE.write_text(yaml.safe_dump(state, allow_unicode=True))


def get_shortcuts(item=None):
    """Get the pinned and recent items for display in the nav menu.
    If item is provided, update the recent items.
    """
    global state
    recent = list(state["recent"])
    if item is not None:
        try:
            recent.remove(item.id)
        except ValueError:
            pass
        write_state(recent=item)
    pinned = list(state["pinned"])
    recent = [id for id in recent if id not in pinned]
    return [get(id) for id in (pinned + recent)]


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
        if not path.suffix == ".md":
            continue
        content = path.read_text()
        m = constants.FRONTMATTER.match(content)
        if not m:
            continue
        frontmatter = yaml.safe_load(m.group(1))
        # Convert tags from YAML list to set.
        try:
            frontmatter["tags"] = set(frontmatter["tags"])
        except KeyError:
            pass
        text = content[m.start(2) :]
        item = TYPES[frontmatter["type"]](path)
        item.frontmatter.update(frontmatter)
        item.text = text
        lookup[item.id] = item

    setup_pointers()


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


def get_items(type=None, key=None):
    "Get all items, or of a given type."
    global lookup
    if type is None:
        result = list(lookup.values())
    else:
        type = type.lower()
        result = [i for i in lookup.values() if i.type == type]
    if key:
        result.sort(key=key)
    return result


def get_all_files():
    "Get a map of item paths and filepaths with their modified timestamps."
    global lookup
    result = {
        constants.STATE_FILE.name: utils.timestamp_utc(
            constants.STATE_FILE.stat().st_mtime
        )
    }
    result = {}
    for item in lookup.values():
        result[item.id] = item.modified
        if isinstance(item, (File, Image)):
            result[str(item.filename)] = item.file_modified
    return result


def get_statistics():
    global TYPES
    result = dict(item=len(lookup))
    result.update(dict([(type, 0) for type in TYPES]))
    for item in lookup.values():
        result[item.type] += 1
    return result
