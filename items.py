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
import settings
import utils

# The item types.
TYPES = ["Note", "Link", "Image", "File", "Database", "Graphic", "Listset"]


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
        self.similarities = {}  # Key: item id; value: similarity number.

    def __str__(self):
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
        assert title
        self.frontmatter["title"] = title
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
    def keywords(self):
        # This is a set, not a list.
        return self.frontmatter.get("keywords") or set()

    @keywords.setter
    def keywords(self, keywords):
        self.frontmatter["keywords"] = set(keywords).intersection(settings.keywords)
        self.set_similarities()

    @property
    def listsets(self):
        "Return the set of listsets this item is part of."
        result = set()
        for item in lookup.values():
            if isinstance(item, Listset):
                if self in item:
                    result.add(item)
        return result

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

    def edit(self, title, text, listsets, keywords):
        """Edit the data of the item.
        Does *not* write out the item.
        *Does* write out the affected listsets.
        """
        self.title = title.strip() or "no title"
        self.text = text.strip()
        for id in listsets or list():
            listset = get(id)
            assert isinstance(listset, Listset)
            listset.add(self)
            listset.write()
        self.keywords = keywords or list()

    def write(self):
        "Write the item to file."
        with self.path.open(mode="w") as outfile:
            if self.frontmatter:
                frontmatter = copy.deepcopy(self.frontmatter)
                if keywords := frontmatter.pop("keywords", None):
                    frontmatter["keywords"] = list(keywords)
                outfile.write("---\n")
                outfile.write(yaml.safe_dump(frontmatter, allow_unicode=True))
                outfile.write("---\n")
            if self.text:
                outfile.write(self.text)

    def delete(self):
        """Delete the item from the file system.
        Remove all similarities to it.
        Remove from all listsets it is part of.
        Remove from the lookup.
        """
        global lookup
        id = self.id
        for item in lookup.values():
            item.similarities.pop(id, None)
        for listset in self.listsets:
            listset.remove(id)
            listset.write()
        lookup.pop(id)
        self.path.unlink()

    def remove_keyword(self, keyword):
        "Remove the keyword from this item, and write it if any change."
        try:
            self.keywords.remove(keyword)
        except KeyError:
            pass
        else:
            self.write()
            self.set_similarities()

    def set_similarities(self):
        "Set the similarities between this item and all others."
        global lookup
        id = self.id
        self.similarities = {}  # Key: item id; value: similarity number.
        for item in lookup.values():
            if item is self:
                continue
            if similarity := self.similarity(item):
                self.similarities[item.id] = similarity
                item.similarities[id] = similarity
            else:
                item.similarities.pop(id, None)

    def similarity(self, other):
        "Return the similarity number between this item and the other."
        assert isinstance(other, Item)
        return len(self.keywords.intersection(other.keywords))

    def similar(self):
        "Return the sorted list of similar items."
        return [
            get(k)
            for k, v in sorted(
                self.similarities.items(), key=lambda r: r[1], reverse=True
            )
        ]

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


class Listset(Item):
    "Listset item class."

    def __contains__(self, item):
        if isinstance(item, Item):
            return item.id in self.frontmatter["items"]
        else:
            return False

    @property
    def items(self):
        return [get(id) for id in self.frontmatter["items"]]

    def flattened(self):
        "Return all subitems, including those in contained listsets."
        result = [self]
        for item in self.items:
            if isinstance(item, Listset):
                result.extend(item.flattened())
            else:
                result.append(item)
        return result

    def add(self, item):
        assert isinstance(item, Item)
        if item in self:
            return
        if isinstance(item, Listset):
            if self in item.flattened():
                raise ValueError("The given listset contains this listset in its tree.")
        self.frontmatter["items"].append(item.id)

    def remove(self, id):
        try:
            self.frontmatter["items"].remove(id)
        except ValueError:
            pass


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
    Compute similarities between the items based on the keywords.
    """
    global lookup
    if dirpath is None:
        lookup.clear()
    for path in constants.DATA_DIR.iterdir():
        if path.is_dir():
            if path.name == ".trash":
                continue
            read_items(path)
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
                item = Link(path)
            elif "filename" in frontmatter:
                mimetype = mimetypes.guess_type(frontmatter["filename"])[0]
                if mimetype in constants.IMAGE_MIMETYPES:
                    item = Image(path)
                elif mimetype == constants.SQLITE_MIMETYPE:
                    item = Database(path)
                else:
                    item = File(path)
            elif "items" in frontmatter:
                item = Listset(path)
            elif "graphic" in frontmatter:
                item = Graphic(path)
            else:
                item = Note(path)
            lookup[item.id] = item
            frontmatter["keywords"] = set(frontmatter.pop("keywords", []))
            item.frontmatter = frontmatter
            item.text = text
    set_all_similarities()


def set_all_similarities():
    "Compute similarities between the items based on the keywords."
    global lookup
    items = list(lookup.values())
    for item in items:
        item.similarities = {}  # Key: item id; value: similarity number.
    for pos, item1 in enumerate(items):
        for item2 in items[pos + 1 :]:
            if similarity := item1.similarity(item2):
                item1.similarities[item2.id] = similarity
                item2.similarities[item1.id] = similarity


def get_items(cls=None):
    "Get all items, or of a given type, sorted by modified time."
    global lookup
    if cls is None:
        result = list(lookup.values())
    else:
        result = [e for e in lookup.values() if isinstance(e, cls)]
    result.sort(key=lambda e: e.modified, reverse=True)
    return result


def get_keyword_items(keyword):
    "Get the items with the given keyword sorted by modified time."
    global lookup
    result = [e for e in lookup.values() if keyword in e.keywords]
    result.sort(key=lambda e: e.modified, reverse=True)
    return result


def get_total_keyword_items(keyword):
    "Return the number of items having the keyword."
    global lookup
    return len([e for e in lookup.values() if keyword in e.keywords])


def get_no_similar_items():
    "Get the items with no similars sorted by modified time."
    global lookup
    result = [i for i in lookup.values() if len(i.similar()) == 0]
    result.sort(key=lambda e: e.modified, reverse=True)
    return result


def get_no_keyword_items():
    "Get the items without keywords sorted by modified time."
    global lookup
    result = [e for e in lookup.values() if not e.keywords]
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


def get_possible_listsets(item):
    "Get the listsets this item could be included in."
    result = []
    for listset in get_items(Listset):
        if item in listset:
            continue
        if item is listset:
            continue
        if isinstance(item, Listset) and item in listset.flattened():
            continue
        result.append(listset)
    return result


def get_statistics():
    result = dict(item=len(lookup))
    result.update(dict([(type.lower(), 0) for type in TYPES]))
    for item in lookup.values():
        result[item.__class__.__name__.lower()] += 1
    result["keyword"] = len(settings.keywords)
    return result
