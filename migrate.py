"Update all Markdown files to new format. Handles all previous formats."

import contextlib
import locale
import os

# This must be done before importing 'constants'.
from dotenv import load_dotenv

if os.environ.get("CHAOS_DEVELOPMENT"):
    with open(".env-development") as infile:
        load_dotenv(stream=infile)
else:
    load_dotenv()

locale.setlocale(locale.LC_ALL, "")


import constants
import items


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
        # Remove timezone info from 'start' and 'end'; for Event items.
        if "start" in item.frontmatter:
            with update(item):
                item.start = item.start.replace(tzinfo=None)
        if "end" in item.frontmatter:
            with update(item):
                item.end = item.end.replace(tzinfo=None)


if __name__ == "__main__":
    pass
    # migrate()
