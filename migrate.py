"Update all Markdown files to new format. Handles all previous formats."

import contextlib
import os

import constants
import items

# Map of event category to tag; some categories are not included.
CATEGORY_EVENT = dict(
    important="viktigt",
    critical="superviktigt",
)


def migrate():
    "Update all Markdown files to the new format. Handles all previous formats."
    for path in constants.DATA_DIR.iterdir():
        item = items.read_item(path)
        if item is None:
            continue
        # Remove 'filename' and add 'ext' instead; for File, Image and Database items.
        if "filename" in item.frontmatter:
            with update(item):
                filename = item.frontmatter.pop("filename")
                filename = pathlib.Path(filename)
                item.ext = filename.suffix
        # For Event items, remove timezone info from 'start' and 'end'.
        if isinstance(item, items.Event):
            if item.start.tzinfo:
                with update(item):
                    item.frontmatter["start"] = item.start.replace(tzinfo=None)
            if item.end.tzinfo:
                with update(item):
                    item.frontmatter["end"] = item.end.replace(tzinfo=None)
            # For Event items, convert category to tag.
            if category := item.frontmatter.pop("category", None):
                with update(item):
                    tags = item.tag_ids
                    try:
                        tags.add(CATEGORY_EVENT[category])
                    except KeyError:
                        pass
                    item.tags = tags
        # For Book items, remove language
        if isinstance(item, items.Book):
            if "language" in item.frontmatter:
                with update(item):
                    item.frontmatter.pop("language")


@contextlib.contextmanager
def update(item):
    "Update the contents of the Markdown file without changing the modification time."
    stat = item.path.stat()
    times = (stat.st_atime, stat.st_mtime)
    try:
        yield item
    finally:
        item.write(refresh=False)
        os.utime(item.path, times=times)
