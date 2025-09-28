"Entry class and functions."

import copy
import datetime
import os
import pathlib
import unicodedata

import babel.dates
import marko
import yaml

import constants

# Key: entry id; value: entry instance.
entries_lookup = {}

class Entry:
    "Entry in notebook."

    def __init__(self, path):
        self.path = path
        self.frontmatter = {}

    def __str__(self):
        return self.eid

    @property
    def eid(self):
        return self.path.stem.casefold()

    @property
    def title(self):
        try:
            return self.frontmatter["title"]
        except KeyError:
            return self.path.stem

    @title.setter
    def title(self, title):
        self.frontmatter["title"] = title

    @property
    def size(self):
        return len(self.content)

    @property
    def link(self):
        return self.frontmatter.get("link")

    @property
    def file(self):
        try:
            ext = self.frontmatter["ext"]
        except KeyError:
            return None
        return self.path.with_suffix(ext)

    @property
    def type(self):
        if self.link:
            return constants.LINK
        elif self.file:
            return constants.FILE
        else:
            return constants.NOTE

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

    def read(self):
        content = self.path.read_text()
        match = constants.FRONTMATTER.match(content)
        if match:
            self.frontmatter = yaml.safe_load(match.group(1))
            # Dates must be represented as strings, not datetime.date.
            for key, value in self.frontmatter.items():
                if isinstance(value, datetime.date):
                    self.frontmatter[key] = str(value)
            self.content = content[match.start(2) :]
        else:
            self.frontmatter = {}
            self.content = content

    def write(self):
        with self.path.open(mode="w") as outfile:
            if self.frontmatter:
                outfile.write("---\n")
                outfile.write(yaml.safe_dump(self.frontmatter, allow_unicode=True))
                outfile.write("---\n")
            if self.content:
                outfile.write(self.content)

    def copy(self):
        global entries_lookup
        new = create_entry(self.title + " [copy]")
        frontmatter = copy.deepcopy(self.frontmatter)
        frontmatter.pop("title")
        new.frontmatter.update(frontmatter)
        new.content = self.content
        # XXX other stuff for link and file.
        new.write()
        return new

    def delete(self):
        global entries_lookup
        entries_lookup.pop(self.eid)
        self.path.unlink()


def read_entry_files(dirpath=None):
    """Recursively read all entries from from files in the given directory.
    If no directory is given, start with the root.
    Create the root if it does not exist.
    """
    global entries_lookup
    if dirpath is None:
        entries_lookup.clear()
        dirpath = pathlib.Path(os.environ["CHAOS_DIR"])
        if not dirpath.exists():
            dirpath.mkdir()
    for path in dirpath.iterdir():
        if path.is_dir():
            read_entry_files(path)
        elif path.is_file() and path.suffix == ".md":
            entry = Entry(path)
            entry.read()
            entries_lookup[entry.eid] = entry

def get(eid):
    global entries_lookup
    return entries_lookup[eid]

def recent(start=0, end=25):
    global entries_lookup
    entries = list(entries_lookup.values())
    entries.sort(key=lambda e: e.modified, reverse=True)
    return list(entries[start:end])

def create_entry(title):
    """Create an entry with the given title.
    The filename of the entry is created from the title
    after cleanup, and made unique, if not already.
    NOTE: The entry is *not* written to file.
    """
    global entries_lookup
    root = pathlib.Path(os.environ["CHAOS_DIR"])
    filename = unicodedata.normalize("NFKD", title).encode("ASCII", "ignore")
    filename = "".join(
        [c.casefold() if c in constants.FILENAME_CHARACTERS else "-" for c in filename.decode("utf-8")]
    )
    path = root / f"{filename}.md"
    if path.exists():
        n = 2
        path = root / f"{filename}-{n}.md"
        while path.exists():
            n += 1
    entry = Entry(path)
    entry.frontmatter["title"] = title
    entries_lookup[entry.eid] = entry
    return entry
