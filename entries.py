"Entry class and functions."

import copy
import datetime
import os
import pathlib
import unicodedata

import babel.dates
from fasthtml.common import Convertor, register_url_convertor
import marko
import yaml

import constants

# Key: entry id; value: entry instance.
entries_lookup = {}


def get(eid):
    global entries_lookup
    return entries_lookup[eid]


class Entry:
    "Abstract entry class."

    def __init__(self, path=None):
        self._path = path
        self.frontmatter = {}

    def __str__(self):
        return self.eid

    @property
    def type(self):
        return self.__class__.__name__.casefold()

    @property
    def path(self):
        return self._path

    @property
    def eid(self):
        return self.path.stem

    @property
    def url(self):
        return f"/{self.type}/{self}"

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
        global entries_lookup
        entries_lookup.pop(self.eid)
        self.path.unlink()


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
        self.filepath.unlink()
        super().delete()


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


def recent(start=0, end=25):
    global entries_lookup
    entries = list(entries_lookup.values())
    entries.sort(key=lambda e: e.modified, reverse=True)
    return list(entries[start:end])
