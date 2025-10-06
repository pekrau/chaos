"Entry class and functions."

import datetime
import os
import pathlib
import random
import re
import unicodedata

import babel.dates
import filetype
import marko
import yaml

import constants
import settings


# Key: entry id; value: entry instance.
lookup = {}


class Entry:
    "Abstract entry class."

    def __init__(self, path=None):
        self._path = path
        self.frontmatter = {}
        self.text = ""
        self.keywords = set()
        self.relations = {}

    def __str__(self):
        return self._path.stem

    @property
    def path(self):
        return self._path

    @property
    def url(self):
        return f"/{self.__class__.__name__.casefold()}/{self}"

    @property
    def owner(self):
        return self.frontmatter["owner"]

    @owner.setter
    def owner(self, owner):
        assert owner
        self.frontmatter["owner"] = owner

    @property
    def title(self):
        try:
            return self.frontmatter["title"]
        except KeyError:
            return self.path.stem

    @title.setter
    def title(self, title):
        "Set the title. If the path has not been set, set it to unique variant."
        global lookup
        assert title
        self.frontmatter["title"] = title
        if self.path is None:
            filename = unicodedata.normalize("NFKD", title).encode("ASCII", "ignore")
            filename = "".join(
                [
                    c if c in constants.FILENAME_CHARACTERS else "-"
                    for c in filename.decode("utf-8")
                ]
            )
            filename = filename.casefold()
            self._path = constants.DATA_DIR / f"{filename}.md"
            if str(self) in lookup:
                n = 2
                while True:
                    self._path = constants.DATA_DIR / f"{filename}-{n}.md"
                    if str(self) not in lookup:
                        break
                    n += 1
            lookup[str(self)] = self

    @property
    def size(self):
        "Size of the entry text, in bytes."
        return len(self.text)

    @property
    def modified(self):
        "Modified timestamp in UTC ISO format."
        return timestamp_utc(self.path.stat().st_mtime)

    @property
    def modified_local(self):
        "Modified timestamp in local ISO format."
        timestamp = self.path.stat().st_mtime
        dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.UTC)
        return babel.dates.format_datetime(
            dt,
            tzinfo=constants.DEFAULT_TIMEZONE,
            locale=constants.DEFAULT_LOCALE,
            format=constants.DATETIME_BABEL_FORMAT,
        )

    def write(self):
        "Write the entry to file."
        with self.path.open(mode="w") as outfile:
            if self.frontmatter:
                outfile.write("---\n")
                outfile.write(yaml.safe_dump(self.frontmatter, allow_unicode=True))
                outfile.write("---\n")
            if self.text:
                outfile.write(self.text)

    def delete(self):
        "Delete the entry from the file system and remove from the lookup."
        global lookup
        self.remove_relations()
        lookup.pop(str(self))
        self.path.unlink()

    def remove_relations(self):
        "Remove all relations from other entries to this one."
        global lookup
        entryid = str(self)
        for entry in lookup.values():
            entry.relations.pop(entryid, None)

    def score(self, term):
        """Calculate the score for the term in the title or text of the entry.
        Presence in the title is weighted heavier.
        """
        rx = re.compile(f"{term.strip()}.*", re.IGNORECASE)
        return constants.SCORE_TITLE_WEIGHT * len(rx.findall(self.title)) + len(
            rx.findall(self.text)
        )

    def set_keywords(self):
        "Find the canonical keywords in the title and text of this entry."
        self.keywords = settings.get_canonical_keywords(self.title).union(
            settings.get_canonical_keywords(self.text)
        )

    def relation(self, other):
        "Return the relation number between this entry and the other."
        assert isinstance(other, Entry)
        return len(self.keywords.intersection(other.keywords))

    def related(self):
        "Return the sorted list of related entries."
        return [
            get(k)
            for k, v in sorted(self.relations.items(), key=lambda r: r[1], reverse=True)
        ]

    def is_unrelated(self):
        "Is this entry not related to any other?"
        if not self.keywords:
            return True
        else:
            return len(self.related()) == 0


class Note(Entry):
    "Note entry class."


class Link(Entry):
    "Link entry class"

    @property
    def href(self):
        return self.frontmatter.get("href") or "/"

    @href.setter
    def href(self, href):
        self.frontmatter["href"] = href.strip() or "/"


class File(Entry):
    "File entry class."

    @property
    def filename(self):
        return pathlib.Path(self.frontmatter["filename"])

    @property
    def filepath(self):
        return constants.DATA_DIR / self.filename

    @property
    def file_size(self):
        "Size of the file, in bytes."
        return self.filepath.stat().st_size

    @property
    def file_extension(self):
        """Return file extension or None if not recognized.
        Determined from file data, not explicit file extension.
        """
        kind = filetype.guess(self.filepath)
        if kind is None:
            return (None, None)
        else:
            return (kind.extension, kind.mime)

    @property
    def file_mimetype(self):
        """Return MIME type, or None if not recognized.
        Determined from file data, not explicit file extension.
        """
        kind = filetype.guess(self.filepath)
        if kind is None:
            None
        else:
            return kind.mime

    @property
    def is_image(self):
        return self.file_mimetype in constants.IMAGE_CONTENT_TYPES

    @property
    def file_modified(self):
        "Modified timestamp in UTC ISO format."
        return timestamp_utc(self.filepath.stat().st_mtime)

    def delete(self):
        "Delete the entry from the file system and its file and remove from the lookup."
        self.filepath.unlink()
        super().delete()


def get(entryid):
    global lookup
    return lookup[entryid]


def read_entry_files(dirpath=None):
    """Recursively read all entries from from files in the given directory.
    If no directory is given, start with the data dir.
    Create the data dir if it does not exist.
    """
    global lookup
    if dirpath is None:
        lookup.clear()
    for path in constants.DATA_DIR.iterdir():
        if path.is_dir():
            read_entry_files(path)
        elif path.is_file() and path.suffix == ".md":
            content = path.read_text()
            match = constants.FRONTMATTER.match(content)
            if match:
                frontmatter = yaml.safe_load(match.group(1))
                # Dates must be represented as strings, not datetime.date.
                for key, value in frontmatter.items():
                    if isinstance(value, datetime.date):
                        frontmatter[key] = str(value)
                text = content[match.start(2) :]
            else:
                frontmatter = {}
                text = content
            if "href" in frontmatter:
                entry = Link(path)
            elif "filename" in frontmatter:
                entry = File(path)
            else:
                entry = Note(path)
            lookup[str(entry)] = entry
            entry.frontmatter = frontmatter
            entry.text = text


def set_all_keywords_relations():
    "Find keywords in all the entries and compute relations between them."
    global lookup
    entries = list(lookup.values())
    for entry in entries:
        entry.set_keywords()
        entry.relations = {}  # Key: entry id; value: relation number.
    for pos, entry1 in enumerate(entries):
        for entry2 in entries[pos + 1 :]:
            if relation := entry1.relation(entry2):
                entry1.relations[str(entry2)] = relation
                entry2.relations[str(entry1)] = relation


def set_keywords_relations(entry):
    "Update the keywords and relations involving the provided entry."
    global lookup
    entry.remove_relations()
    entry.set_keywords()
    for entry2 in lookup.values():
        if entry2 is entry:
            continue
        if relation := entry.relation(entry2):
            entry.relations[str(entry2)] = relation
            entry2.relations[str(entry)] = relation


def get_recent_entries(start=0, end=constants.MAX_PAGE_ENTRIES, keyword=None):
    """Get the entries ordered by modified time, optionally filtered by keyword.
    If start is None, then return all entries.
    """
    assert (start is None) or (start >= 0)
    assert (end is None) or (end > start)
    if keyword:
        result = []
        for entry in lookup.values():
            if keyword in entry.keywords:
                result.append(entry)
    else:
        result = list(lookup.values())
    result.sort(key=lambda e: e.modified, reverse=True)
    if (start is None) or (end is None):
        return result
    else:
        return result[start:end]


def get_unrelated_entries(start=0, end=constants.MAX_PAGE_ENTRIES):
    """Get the unrelated entries ordered by modified time.
    If start is None, then return all entries.
    """
    result = [e for e in lookup.values() if e.is_unrelated()]
    result.sort(key=lambda e: e.modified, reverse=True)
    if (start is None) or (end is None):
        return result
    else:
        return result[start:end]


def get_no_keyword_entries(start=0, end=constants.MAX_PAGE_ENTRIES):
    """Get the entries without keywords ordered by modified time.
    If start is None, then return all entries.
    """
    result = [e for e in lookup.values() if not e.keywords]
    result.sort(key=lambda e: e.modified, reverse=True)
    if start is None:
        return result
    else:
        return result[start:end]


def get_random_entries():
    "Get a set of at most MAX_PAGE_ENTRIES random entries."
    entries = list(lookup.values())
    if len(entries) <= constants.MAX_PAGE_ENTRIES:
        random.shuffle(entries)
        return entries
    else:
        return random.sample(entries, constants.MAX_PAGE_ENTRIES)


def get_all():
    "Get a map of entry paths and filepaths with their modified timestamps."
    result = {}
    for entry in lookup.values():
        result[str(entry)] = entry.modified
        if isinstance(entry, File):
            result[str(entry.filename)] = entry.file_modified
    result[".chaos.yaml"] = timestamp_utc(
        (constants.DATA_DIR / ".chaos.yaml").stat().st_mtime
    )
    return result


def timestamp_utc(timestamp):
    dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.UTC)
    return dt.strftime(constants.DATETIME_ISO_FORMAT)


def count(keyword):
    "Return the number of entries having the keyword."
    return len([e for e in lookup.values() if keyword in e.keywords])
