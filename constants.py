"Various constants."

import os
import pathlib
import re
import string

import babel.dates

VERSION = (0, 12, 0)
__version__ = ".".join([str(n) for n in VERSION])

GITHUB_URL = "https://github.com/pekrau/chaos"

DATA_DIR = pathlib.Path(os.environ["CHAOS_DIR"])
if not DATA_DIR.exists():
    raise OSError(f"DATA_DIR {DATA_DIR} does not exist")

FILENAME_CHARACTERS = set(string.ascii_letters + string.digits + "-")

FRONTMATTER = re.compile(r"^---([\n\r].*?[\n\r])---[\n\r](.*)$", re.DOTALL)

DEFAULT_LOCALE = "sv_SE"
DEFAULT_TIMEZONE = babel.dates.get_timezone("Europe/Stockholm")
DATETIME_BABEL_FORMAT = "yyyy-MM-dd HH:mm:ss"
DATETIME_ISO_FORMAT = "%Y-%m-%d %H:%M:%S"

BINARY_MIMETYPE = "application/octet-stream"
GZIP_MIMETYPE = "application/gzip"
PNG_MIMETYPE = "image/png"
JPEG_MIMETYPE = "image/jpeg"
WEBP_MIMETYPE = "image/webp"
GIF_MIMETYPE = "image/gif"
PDF_MIMETYPE = "application/pdf"
DOCX_MIMETYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
EPUB_MIMETYPE = "application/epub+zip"


IMAGE_MIMETYPES = {
    PNG_MIMETYPE,
    JPEG_MIMETYPE,
    WEBP_MIMETYPE,
    GIF_MIMETYPE,
}

OCR_LANGUAGES = ["sv", "en"]
OCR_GPU = bool(os.environ.get("CHAOS_OCR_GPU"))

TEXTUAL_MIMETYPES = {
    PDF_MIMETYPE,
    DOCX_MIMETYPE,
    EPUB_MIMETYPE,
}

MAX_PAGE_ENTRIES = 20
MAX_ROW_KEYWORDS = 5
N_GALLERY_ROW_ITEMS = 5

SCORE_TITLE_WEIGHT = 2.0
