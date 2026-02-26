"Various utility functions."

import datetime
import unicodedata

import babel.dates
import babel.numbers
import webcolors

import constants


def timestamp_utc(timestamp):
    "Convert timestamp to ISO format string in UTC time."
    return datetime.datetime.fromtimestamp(timestamp, tz=datetime.UTC).strftime(
        constants.DATETIME_ISO_FORMAT
    )


def timestamp_local(timestamp):
    "Convert timestamp to ISO format string in local time."
    return babel.dates.format_datetime(
        datetime.datetime.fromtimestamp(timestamp, tz=datetime.UTC),
        tzinfo=constants.DEFAULT_TIMEZONE,
        locale=constants.DEFAULT_LOCALE,
        format=constants.DATETIME_BABEL_FORMAT,
    )


def normalize(s):
    "Normalize string to ASCII, lower case, replacing non-file characters with '-'."
    result = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore")
    result = "".join(
        [
            c if c in constants.FILENAME_CHARACTERS else "-"
            for c in result.decode("utf-8")
        ]
    )
    return result.casefold()


def numerical(n):
    "Return numerical value as string formatted according to locale."
    return babel.numbers.format_decimal(n, locale=constants.DEFAULT_LOCALE)


def to_hex_color(color):
    "Convert to hex color, if not already."
    if not color:
        color = "black"
    if not color.startswith("#"):
        try:
            color = webcolors.name_to_hex(color)
        except ValueError:
            color = "black"
    return color


def to_name_color(color):
    "Convert to name color, or keep in hex."
    if color.startswith("#"):
        try:
            color = webcolors.hex_to_name(color)
        except ValueError:
            pass
    return color
