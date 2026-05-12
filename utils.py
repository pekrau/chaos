"Various utility functions."

import datetime as dt
import os
import unicodedata

import babel.numbers
import webcolors

import constants


def timestamp_utc(timestamp):
    "Convert timestamp to ISO format string in UTC time."
    return dt.datetime.fromtimestamp(timestamp, tz=dt.UTC).strftime("%Y-%m-%d %H:%M:%S")


def get_datetime(year, month, day=1):
    "Return the datetime instance for the given day."
    return dt.datetime(year, month, day, tzinfo=constants.TIMEZONE)


def to_datetime(date, hour=0, minute=0):
    "Convert the date instance to datetime."
    if isinstance(date, dt.datetime):
        return date
    return dt.datetime.combine(date, dt.time(hour, minute, tzinfo=constants.TIMEZONE))


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


def numerical(n):
    "Return numerical value as string formatted according to locale."
    return babel.numbers.format_decimal(n, locale=os.environ.get("LC_MONETARY"))


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


def get_total_pages(total_items):
    "Return the total number of table pages for the given number of items."
    return (total_items - 1) // constants.MAX_PAGE_ITEMS + 1
