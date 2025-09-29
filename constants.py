"Various constants."

import os
import pathlib
import re
import string

import babel.dates

VERSION = "0.3"

DATA_DIR = pathlib.Path(os.environ["CHAOS_DIR"])

FILENAME_CHARACTERS = set(string.ascii_letters + string.digits + "-")

FRONTMATTER = re.compile(r"^---([\n\r].*?[\n\r])---[\n\r](.*)$", re.DOTALL)

DEFAULT_LOCALE = "sv_SE"
DEFAULT_TIMEZONE = babel.dates.get_timezone("Europe/Stockholm")
DATETIME_BABEL_FORMAT = "yyyy-MM-dd H:mm:ss"
DATETIME_ISO_FORMAT = "%Y-%m-%d %H:%M:%S"

NAV_STYLE = "outline-color:lightgrey; outline-width:4px; outline-style:solid; padding:0px 10px; border-radius:4px;"

MAIN_NAV_STYLE = "outline-color:lightgrey; outline-width:4px; outline-style:solid; padding:0px 10px; border-radius:4px;"

NOTE_NAV_STYLE = "outline-color:forestgreen; outline-width:4px; outline-style:solid; padding:0px 10px; border-radius:4px;"

LINK_NAV_STYLE = "outline-color:dodgerblue; outline-width:4px; outline-style:solid; padding:0px 10px; border-radius:4px;"

FILE_NAV_STYLE = "outline-color:goldenrod; outline-width:4px; outline-style:solid; padding:0px 10px; border-radius:4px;"

NOTE = "note"
LINK = "link"
FILE = "file"
TYPES = (NOTE, LINK, FILE)
