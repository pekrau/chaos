"Various utility functions."

import datetime as dt
import os
import os.path
import shutil
import sys
import time
import unicodedata

import yaml

import constants


def iso_from_timestamp(timestamp=None, tz=dt.UTC):
    "Convert timestamp to ISO format string in UTC timezone."
    return dt.datetime.fromtimestamp(timestamp or time.time(), tz=tz).strftime("%Y-%m-%d %H:%M:%S")


def get_datetime(year, month, day=1):
    "Return the datetime instance for the given day."
    return dt.datetime(year, month, day)


def to_datetime(date, hour=0, minute=0):
    "Convert the date instance to datetime."
    if isinstance(date, dt.datetime):
        return date
    return dt.datetime.combine(date, dt.time(hour, minute))


def normalize(s):
    "Normalize string to ASCII, fold case, replace non-file characters with '-'."
    result = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore")
    result = "".join(
        [
            c if c in constants.FILENAME_CHARACTERS else "-"
            for c in result.decode("utf-8")
        ]
    )
    return result.casefold()


def get_total_pages(total_items):
    "Return the total number of table pages for the given number of items."
    return (total_items - 1) // constants.MAX_PAGE_ITEMS + 1


def split_markdown(content):
    "Split the Markdown file content into frontmatter and text."
    m = constants.FRONTMATTER.match(content)
    if not m:
        raise ValueError
    frontmatter = yaml.safe_load(m.group(1))
    try:
        frontmatter["tags"] = set(frontmatter["tags"])
    except KeyError:
        pass
    return (frontmatter, content[m.start(2) :])
