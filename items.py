"Item class and functions."

import copy
import datetime
import mimetypes
import os
import pathlib
import random
import re
import sqlite3

import filetype
import marko
import yaml

import constants
import errors
import utils

# The item types.
TYPES = ["Note", "Link", "Image", "File", "Database", "Graphic"]


# Global item lookup. Key: item id; value: item instance.
lookup = {}


def get(itemid):
    "Get the item from the global lookup given its identifier."
    global lookup
    return lookup[itemid]


class Item:
    "Abstract item class."

    def __init__(self, path=None):
        self._path = path
        self.frontmatter = {}
        self.text = ""
        self.xrefs_from_self = set()
        self.xrefs_to_self = set()

    def __str__(self):
        return self.url

    def __repr__(self):
        return self.url

    @property
    def name(self):
        return self.__class__.__name__.lower()

    @property
    def id(self):
        return self.path.stem

    @property
    def path(self):
        return self._path

    @property
    def url(self):
        return f"/{self.__class__.__name__.casefold()}/{self.id}"

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
        return utils.timestamp_local(self.path.stat().st_mtime)

    def write(self):
        """Write the item to file.
        Update the relevant 'xrefs_from_self' and 'xrefs_to_self' for the item.
        """
        with self.path.open(mode="w") as outfile:
            if self.frontmatter:
                frontmatter = copy.deepcopy(self.frontmatter)
                outfile.write("---\n")
                outfile.write(yaml.safe_dump(frontmatter, allow_unicode=True))
                outfile.write("---\n")
            if self.text:
                outfile.write(self.text)
        old_xrefs_from_self = set(self.xrefs_from_self)
        self.xrefs_from_self.clear()
        # Which items are currently referenced by this item?
        for m in constants.XREF.finditer(self.text):
            try:
                other = get(m.group(1))
            except KeyError:
                pass
            else:
                self.xrefs_from_self.add(other.id)
                other.xrefs_to_self.add(self.id)
        # Remove reference from items that are no longer referenced by this.
        for id in old_xrefs_from_self.difference(self.xrefs_from_self):
            get(id).xrefs_from_self.remove(self.id)

    def delete(self):
        """Delete the item from the file system.
        Remove references to it from other items.
        Remove from the lookup.
        """
        global lookup
        for id in self.xrefs_to_self:
            get(id).xrefs_from_self.remove(self.id)
        for id in self.xrefs_from_self:
            get(id).xrefs_to_self.remove(self.id)
        self.path.unlink()
        lookup.pop(self.id)

    def score(self, term):
        """Calculate the score for the term in the title or text of the item.
        Presence in the title is weighted heavier.
        """
        rx = re.compile(f"{term.strip()}.*", re.IGNORECASE)
        return constants.SCORE_TITLE_WEIGHT * len(rx.findall(self.title)) + len(
            rx.findall(self.text)
        )


class Note(Item):
    "Note item class."


class Link(Item):
    "Link item class."

    @property
    def href(self):
        return self.frontmatter.get("href") or "/"

    @href.setter
    def href(self, href):
        self.frontmatter["href"] = href.strip() or "/"


class GenericFile(Item):
    "Generic file item class."

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


class Image(GenericFile):
    "Image item class."

    pass


class File(GenericFile):
    "File item class."

    pass


class Database(GenericFile):
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

    @property
    def plots(self):
        return self.frontmatter.get("plots") or {}


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


def read_items(dirpath=None):
    """Recursively read all items from files in the given directory.
    If no directory is given, start with the data dir.
    Create the data dir if it does not exist.
    """
    global lookup
    if dirpath is None:
        lookup.clear()
    for path in constants.DATA_DIR.iterdir():
        if path.is_dir():
            read_items(path)
        elif path.is_file() and path.suffix == ".md":
            content = path.read_text()
            m = constants.FRONTMATTER.match(content)
            if m:
                frontmatter = yaml.safe_load(m.group(1))
                # Dates must be represented as strings, not datetime.date.
                for key, value in frontmatter.items():
                    if isinstance(value, datetime.date):
                        frontmatter[key] = str(value)
                text = content[m.start(2) :]
            else:
                frontmatter = {}
                text = content
            # Which type of item depends on the presence of a keyword in front matter.
            if "href" in frontmatter:
                item = Link(path)
            elif "filename" in frontmatter:
                mimetype = mimetypes.guess_type(frontmatter["filename"])[0]
                if mimetype in constants.IMAGE_MIMETYPES:
                    item = Image(path)
                elif mimetype == constants.SQLITE_MIMETYPE:
                    item = Database(path)
                else:
                    item = File(path)
            elif "graphic" in frontmatter:
                item = Graphic(path)
            else:
                item = Note(path)
            lookup[item.id] = item
            item.frontmatter = frontmatter
            item.text = text


def setup_all_xrefs():
    "Set the 'xrefs_from' and 'xrefs_to' for item xrefs."
    for item in lookup.values():
        item.xrefs_from_self.clear()
        item.xrefs_to_self.clear()
    for item in lookup.values():
        for m in constants.XREF.finditer(item.text):
            try:
                other = get(m.group(1))
            except KeyError:
                pass
            else:
                item.xrefs_from_self.add(other.id)
                other.xrefs_to_self.add(item.id)


def get_items(cls=None):
    "Get all items, or of a given type, sorted by modified time."
    global lookup
    if cls is None:
        result = list(lookup.values())
    else:
        result = [e for e in lookup.values() if isinstance(e, cls)]
    result.sort(key=lambda e: e.modified, reverse=True)
    return result


def get_random_items():
    "Get a set of at most MAX_PAGE_ITEMS random items."
    global lookup
    items = list(lookup.values())
    if len(items) <= constants.MAX_PAGE_ITEMS:
        random.shuffle(items)
        return items
    else:
        return random.sample(items, constants.MAX_PAGE_ITEMS)


def get_all():
    "Get a map of item paths and filepaths with their modified timestamps."
    global lookup
    result = {
        ".chaos.yaml": utils.timestamp_utc(
            (constants.DATA_DIR / ".chaos.yaml").stat().st_mtime
        )
    }
    for item in lookup.values():
        result[item.id] = item.modified
        if isinstance(item, (File, Image)):
            result[str(item.filename)] = item.file_modified
    return result


def get_statistics():
    result = dict(item=len(lookup))
    result.update(dict([(type.lower(), 0) for type in TYPES]))
    for item in lookup.values():
        result[item.__class__.__name__.lower()] += 1
    return result
