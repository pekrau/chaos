"Entry class and functions."

import datetime
import mimetypes
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
        self.relations = {}  # Key: entry id; value: relation number.

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
    def keywords(self):
        # This is a set, not a list.
        return self.frontmatter["keywords"]

    @keywords.setter
    def keywords(self, keywords):
        self.frontmatter["keywords"] = set(keywords).intersection(settings.keywords)
        self.set_relations()

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
                frontmatter = self.frontmatter.copy()
                frontmatter["keywords"] = list(frontmatter.pop("keywords", []))
                outfile.write("---\n")
                outfile.write(yaml.safe_dump(frontmatter, allow_unicode=True))
                outfile.write("---\n")
            if self.text:
                outfile.write(self.text)

    def delete(self):
        """Delete the entry from the file system.
        Remove all relations to it.
        Remove from the lookup.
        """
        global lookup
        id = str(self)
        for entry in lookup.values():
            entry.relations.pop(id, None)
        lookup.pop(id)
        self.path.unlink()

    def remove_keyword(self, keyword):
        "Remove the keyword from this entry, and write it if any change."
        try:
            self.keyword.remove(keyword)
        except KeyError:
            pass
        else:
            self.write()
            self.set_relations()

    def set_relations(self):
        "Set the relations between this entry and all others."
        global lookup
        id = str(self)
        self.relations = {}  # Key: entry id; value: relation number.
        for entry in lookup.values():
            if entry is self:
                continue
            if relation := self.relation(entry):
                self.relations[str(entry)] = relation
                entry.relations[id] = relation
            else:
                entry.relations.pop(id, None)

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

    def score(self, term):
        """Calculate the score for the term in the title or text of the entry.
        Presence in the title is weighted heavier.
        """
        rx = re.compile(f"{term.strip()}.*", re.IGNORECASE)
        return constants.SCORE_TITLE_WEIGHT * len(rx.findall(self.title)) + len(
            rx.findall(self.text)
        )


class Note(Entry):
    "Note entry class."


class Link(Entry):
    "Link entry class."

    @property
    def href(self):
        return self.frontmatter.get("href") or "/"

    @href.setter
    def href(self, href):
        self.frontmatter["href"] = href.strip() or "/"


class GenericFile(Entry):
    "Generic file entry class."

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
    def file_modified(self):
        "Modified timestamp in UTC ISO format."
        return timestamp_utc(self.filepath.stat().st_mtime)

    def delete(self):
        "Delete the entry and file from the file system and remove from the lookup."
        self.filepath.unlink()
        super().delete()


class Image(GenericFile):
    "Image entry class."

    pass


class File(GenericFile):
    "File entry class."

    pass


def get(entryid):
    global lookup
    return lookup[entryid]


def read_entries(dirpath=None):
    """Recursively read all entries from files in the given directory.
    If no directory is given, start with the data dir.
    Create the data dir if it does not exist.
    Compute relations between the entries based on the keywords.
    """
    global lookup
    if dirpath is None:
        lookup.clear()
    for path in constants.DATA_DIR.iterdir():
        if path.is_dir():
            if path.name == ".trash":
                continue
            read_entries(path)
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
                if (
                    mimetypes.guess_type(frontmatter["filename"])[0]
                    in constants.IMAGE_MIMETYPES
                ):
                    entry = Image(path)
                else:
                    entry = File(path)
            else:
                entry = Note(path)
            lookup[str(entry)] = entry
            frontmatter["keywords"] = set(frontmatter.pop("keywords", []))
            entry.frontmatter = frontmatter
            entry.text = text
    set_all_relations()


def set_all_relations():
    "Compute relations between the entries based on the keywords."
    global lookup
    entries = list(lookup.values())
    for entry in entries:
        entry.relations = {}  # Key: entry id; value: relation number.
    for pos, entry1 in enumerate(entries):
        for entry2 in entries[pos + 1 :]:
            if relation := entry1.relation(entry2):
                entry1.relations[str(entry2)] = relation
                entry2.relations[str(entry1)] = relation


def get_entries():
    "Get all entries sorted by modified time."
    global lookup
    result = list(lookup.values())
    result.sort(key=lambda e: e.modified, reverse=True)
    return result


def get_notes():
    "Get all note entries sorted by modified time."
    global lookup
    result = [e for e in lookup.values() if isinstance(e, Note)]
    result.sort(key=lambda e: e.modified, reverse=True)
    return result


def get_links():
    "Get all link entries sorted by modified time."
    global lookup
    result = [e for e in lookup.values() if isinstance(e, Link)]
    result.sort(key=lambda e: e.modified, reverse=True)
    return result


def get_files():
    "Get all file entries sorted by modified time."
    global lookup
    result = [e for e in lookup.values() if isinstance(e, File)]
    result.sort(key=lambda e: e.modified, reverse=True)
    return result


def get_images():
    "Get all image entries sorted by modified time."
    global lookup
    result = [e for e in lookup.values() if isinstance(e, Image)]
    result.sort(key=lambda e: e.modified, reverse=True)
    return result


def get_keyword_entries(keyword):
    "Get the entries with the given keyword sorted by modified time."
    global lookup
    result = [e for e in lookup.values() if keyword in e.keywords]
    result.sort(key=lambda e: e.modified, reverse=True)
    return result


def get_total_keyword_entries(keyword):
    "Return the number of entries having the keyword."
    global lookup
    return len([e for e in lookup.values() if keyword in e.keywords])


def get_unrelated_entries():
    "Get the unrelated entries sorted by modified time."
    global lookup
    result = [e for e in lookup.values() if len(e.related) == 0]
    result.sort(key=lambda e: e.modified, reverse=True)
    return result


def get_no_keyword_entries():
    "Get the entries without keywords sorted by modified time."
    global lookup
    result = [e for e in lookup.values() if not e.keywords]
    result.sort(key=lambda e: e.modified, reverse=True)
    return result


def get_random_entries():
    "Get a set of at most MAX_PAGE_ENTRIES random entries."
    global lookup
    entries = list(lookup.values())
    if len(entries) <= constants.MAX_PAGE_ENTRIES:
        random.shuffle(entries)
        return entries
    else:
        return random.sample(entries, constants.MAX_PAGE_ENTRIES)


def get_process_entries(process):
    "Get the set of entries with the specified process request."
    global lookup
    return [e for e in lookup.values() if e.frontmatter.get("process") == process]


def get_all():
    "Get a map of entry paths and filepaths with their modified timestamps."
    global lookup
    result = {
        ".chaos.yaml": timestamp_utc(
            (constants.DATA_DIR / ".chaos.yaml").stat().st_mtime
        )
    }
    for entry in lookup.values():
        result[str(entry)] = entry.modified
        if isinstance(entry, (File, Image)):
            result[str(entry.filename)] = entry.file_modified
    return result


def timestamp_utc(timestamp):
    return datetime.datetime.fromtimestamp(timestamp, tz=datetime.UTC).strftime(
        constants.DATETIME_ISO_FORMAT
    )


def get_statistics():
    result = {
        "# entries": len(lookup),
        "# notes": 0,
        "# links": 0,
        "# images": 0,
        "# files": 0,
    }
    for entry in lookup.values():
        match entry.__class__.__name__:
            case "Note":
                result["# notes"] += 1
            case "Link":
                result["# links"] += 1
            case "Image":
                result["# images"] += 1
            case "File":
                result["# files"] += 1
    result["# keywords"] = len(settings.keywords)
    return result
