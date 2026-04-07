"Various constants."

import os
import pathlib
import re
import string

import babel.dates

VERSION = (1, 4, 6)
__version__ = ".".join([str(n) for n in VERSION])

GITHUB_URL = "https://github.com/pekrau/chaos"
ISBN_URL = "https://isbnsearch.org/isbn/{isbn}"
DOI_URL = "https://doi.org/{doi}"
PUBMED_URL = "https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

TABULATOR_VERSION = "6.4.0"

DATA_DIR = pathlib.Path(os.environ["CHAOS_DIR"])
if not DATA_DIR.exists():
    raise OSError(f"DATA_DIR {DATA_DIR} does not exist")

STATE_FILE = DATA_DIR / ".state.yaml"

FILENAME_CHARACTERS = set(string.ascii_letters + string.digits + "-")

FRONTMATTER = re.compile(r"^---([\n\r].*?[\n\r])---[\n\r](.*)$", re.DOTALL)
REF = re.compile(r"\[\[([0-9a-z-]+)\]\]", re.IGNORECASE)

DEFAULT_LOCALE = "sv_SE"
DEFAULT_TIMEZONE = babel.dates.get_timezone("Europe/Stockholm")
DATETIME_BABEL_FORMAT = "yyyy-MM-dd HH:mm:ss"
DATETIME_ISO_FORMAT = "%Y-%m-%d %H:%M:%S"

LANGUAGES = dict(
    en="English",
    se="Svenska",
)

TEXT_MIMETYPE = "text/plain"
BINARY_MIMETYPE = "application/octet-stream"
GZIP_MIMETYPE = "application/gzip"
PNG_MIMETYPE = "image/png"
JPEG_MIMETYPE = "image/jpeg"
SVG_MIMETYPE = "image/svg+xml"
WEBP_MIMETYPE = "image/webp"
GIF_MIMETYPE = "image/gif"
PDF_MIMETYPE = "application/pdf"
DOCX_MIMETYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
EPUB_MIMETYPE = "application/epub+zip"
SQLITE_MIMETYPE = "application/vnd.sqlite3"
CSV_MIMETYPE = "text/csv"
JSON_MIMETYPE = "application/json"

IMAGE_MIMETYPES = {
    PNG_MIMETYPE,
    JPEG_MIMETYPE,
    SVG_MIMETYPE,
    WEBP_MIMETYPE,
    GIF_MIMETYPE,
}

MAX_PAGE_ITEMS = 20
N_GALLERY_ROW_ITEMS = 5
MAX_RECENT_ITEMS = 6

SCORE_TITLE_WEIGHT = 2.0

SVG = "SVG"
VEGA_LITE = "Vega-Lite"
GRAPHIC_TYPES = [SVG, VEGA_LITE]
