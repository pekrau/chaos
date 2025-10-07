"Various constants."

import os
import pathlib
import re
import string

import babel.dates

VERSION = (0, 11, 8)
__version__ = ".".join([str(n) for n in VERSION])

DEVELOPMENT = bool(os.environ.get("CHAOS_DEVELOPMENT"))

if DEVELOPMENT:
    DATA_DIR = pathlib.Path(os.environ["CHAOS_DIR_DEVELOPMENT"])
else:
    DATA_DIR = pathlib.Path(os.environ["CHAOS_DIR"])
if not DATA_DIR.exists():
    raise OSError(f"DATA_DIR {constants.DATA_DIR} does not exist")

FILENAME_CHARACTERS = set(string.ascii_letters + string.digits + "-")

FRONTMATTER = re.compile(r"^---([\n\r].*?[\n\r])---[\n\r](.*)$", re.DOTALL)

DEFAULT_LOCALE = "sv_SE"
DEFAULT_TIMEZONE = babel.dates.get_timezone("Europe/Stockholm")
DATETIME_BABEL_FORMAT = "yyyy-MM-dd HH:mm:ss"
DATETIME_ISO_FORMAT = "%Y-%m-%d %H:%M:%S"

BINARY_CONTENT_TYPE = "application/octet-stream"
GZIP_CONTENT_TYPE = "application/gzip"
PNG_CONTENT_TYPE = "image/png"
JPEG_CONTENT_TYPE = "image/jpeg"
WEBP_CONTENT_TYPE = "image/webp"
GIF_CONTENT_TYPE = "image/gif"
PDF_CONTENT_TYPE = "application/pdf"
DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
EPUB_CONTENT_TYPE = "application/epub+zip"


IMAGE_CONTENT_TYPES = {
    PNG_CONTENT_TYPE,
    JPEG_CONTENT_TYPE,
    WEBP_CONTENT_TYPE,
    GIF_CONTENT_TYPE,
}

OCR_LANGUAGES = ["sv", "en"]
OCR_GPU = bool(os.environ.get("CHAOS_OCR_GPU"))

TEXTUAL_CONTENT_TYPES = {
    PDF_CONTENT_TYPE,
    DOCX_CONTENT_TYPE,
    EPUB_CONTENT_TYPE,
}

MAX_PAGE_ENTRIES = 20
MAX_ROW_ITEMS = 5

SCORE_TITLE_WEIGHT = 2.0
