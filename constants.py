"Various constants."

import os
import pathlib
import re
import string

import babel.dates

VERSION = "0.7.0"

DEVELOPMENT = bool(os.environ.get("CHAOS_DEVELOPMENT"))

DATA_DIR = pathlib.Path(os.environ["CHAOS_DIR"])
if not DATA_DIR.exists():
    raise OSError(f"DATA_DIR {constants.DATA_DIR} does not exist")

FILENAME_CHARACTERS = set(string.ascii_letters + string.digits + "-")

FRONTMATTER = re.compile(r"^---([\n\r].*?[\n\r])---[\n\r](.*)$", re.DOTALL)

DEFAULT_LOCALE = "sv_SE"
DEFAULT_TIMEZONE = babel.dates.get_timezone("Europe/Stockholm")
DATETIME_BABEL_FORMAT = "yyyy-MM-dd H:mm:ss"
DATETIME_ISO_FORMAT = "%Y-%m-%d %H:%M:%S"

BINARY_CONTENT_TYPE = "application/octet-stream"
GZIP_CONTENT_TYPE = "application/gzip"

IMAGE_SUFFIXES = set(
    [
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".webp",
    ]
)

SCORE_TITLE_WEIGHT = 2.0
MAX_PAGE_ENTRIES = 25
MAX_ROW_ITEMS = 5
