"Entry class and functions."

import copy
import datetime
import os
import pathlib
import re
import unicodedata

import babel.dates
from fasthtml.common import Convertor, register_url_convertor
import marko
import yaml

import constants
import settings


class Entry:
    "Abstract entry class."

    def __init__(self, path=None):
        self._path = path
        self.frontmatter = {}
        self.keywords = set()
        self.relations = {}

    def __str__(self):
        return self.eid

    @property
    def path(self):
        return self._path

    @property
    def eid(self):
        return self.path.stem

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
        global entries_lookup
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
            if self.eid in entries_lookup:
                n = 2
                while True:
                    self._path = constants.DATA_DIR / f"{filename}-{n}.md"
                    if self.eid not in entries_lookup:
                        break
                    n += 1
            entries_lookup[self.eid] = self

    @property
    def size(self):
        "Size of the entry content, in bytes."
        return len(self.content)

    @property
    def modified(self):
        "Modified timestamp in UTC ISO format."
        timestamp = self.path.stat().st_mtime
        dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.UTC)
        return dt.strftime(constants.DATETIME_ISO_FORMAT)

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
            if self.content:
                outfile.write(self.content)

    def delete(self):
        "Delete the entry from the file system and remove from the lookup."
        global entries_lookup
        entries_lookup.pop(self.eid)
        self.path.unlink()

    def score(self, term):
        """Calculate the score for the term in the title or text of the entry.
        Presence in the title is weighted by 2.
        """
        rx = re.compile(f"{term.strip()}.*", re.IGNORECASE)
        return 2.0 * len(rx.findall(self.title)) + len(rx.findall(self.content))

    def set_keywords(self):
        "Find keywords in the title and content of this entry."
        self.keywords = settings.get_keywords(self.title).union(settings.get_keywords(self.content))

    def relation(self, other):
        "Return the relation number between this entry and the other."
        assert isinstance(other, Entry)
        return len(self.keywords.intersection(other.keywords))

    def related(self):
        "Return the sorted list of related entries."
        return [get(k) for k, v in sorted(self.relations.items(), key=lambda r: r[1], reverse=True)]


class EntryConvertor(Convertor):
    "Convert path segment to Entry class instance."

    regex = "[^./]+"

    def convert(self, value: str) -> Entry:
        return get(value)

    def to_string(self, value: Entry) -> str:
        return str(value)


register_url_convertor("Entry", EntryConvertor())


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
    def filesize(self):
        "Size of the file, in bytes."
        return self.filepath.stat().st_size

    def delete(self):
        "Delete the entry from the file system and its file and remove from the lookup."
        self.filepath.unlink()
        super().delete()


# Key: entry id; value: entry instance.
entries_lookup = {}


def get(eid):
    global entries_lookup
    return entries_lookup[eid]


def read_entry_files(dirpath=None):
    """Recursively read all entries from from files in the given directory.
    If no directory is given, start with the data dir.
    Create the data dir if it does not exist.
    """
    global entries_lookup
    if dirpath is None:
        entries_lookup.clear()
        if not constants.DATA_DIR.exists():
            constants.DATA_DIR.mkdir()
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
                content = content[match.start(2) :]
            else:
                frontmatter = {}
            if "href" in frontmatter:
                entry = Link(path)
            elif "filename" in frontmatter:
                entry = File(path)
            else:
                entry = Note(path)
            entries_lookup[entry.eid] = entry
            entry.frontmatter = frontmatter
            entry.content = content

def set_all_keywords_relations():
    "Find keywords in all the entries and compute relations between them."
    global entries_lookup
    entries = list(entries_lookup.values())
    for entry in entries:
        entry.set_keywords()
        entry.relations = {}    # Key: entry id; value: relation number.
    for pos, entry1 in enumerate(entries):
        for entry2 in entries[pos+1:]:
            if relation := entry1.relation(entry2):
                entry1.relations[entry2.eid] = relation
                entry2.relations[entry1.eid] = relation


def set_keywords_relations(entry):
    "Update the keywords and relations involving the provided entry."
    global entries_lookup
    entry.set_keywords()
    for entry2 in entries_lookup.values():
        entry2.relations.pop(entry.eid, None)
    for entry2 in entries_lookup.values():
        if entry2 is entry:
            continue
        if relation := entry.relation(entry2):
            entry.relations[entry2.eid] = relation
            entry2.relations[entry.eid] = relation


def recent(start=0, end=25):
    global entries_lookup
    entries = list(entries_lookup.values())
    entries.sort(key=lambda e: e.modified, reverse=True)
    return list(entries[start:end])
