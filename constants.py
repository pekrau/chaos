"Various constants."

import re
import string

import babel.dates

VERSION = "0.1"

FILENAME_CHARACTERS = set(string.ascii_letters + string.digits + "-")

FRONTMATTER = re.compile(r"^---([\n\r].*?[\n\r])---[\n\r](.*)$", re.DOTALL)

DEFAULT_LOCALE = "sv_SE"
DEFAULT_TIMEZONE = babel.dates.get_timezone("Europe/Stockholm")
DATETIME_BABEL_FORMAT = "yyyy-MM-dd H:mm:ss"
DATETIME_ISO_FORMAT = "%Y-%m-%d %H:%M:%S"

NAV_STYLE = "outline-color:lightgrey; outline-width:4px; outline-style:solid; padding:0px 10px; border-radius:4px;"

NOTE = "note"
LINK = "link"
FILE = "file"
TYPES = (NOTE, LINK, FILE)
