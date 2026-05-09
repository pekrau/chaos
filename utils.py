"Various utility functions."

import datetime
import os
import unicodedata

import babel.numbers
import webcolors

import constants


def timestamp_utc(timestamp):
    "Convert timestamp to ISO format string in UTC time."
    return datetime.datetime.fromtimestamp(timestamp, tz=datetime.UTC).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def date(date, weekday=True, year=None):
    "Return representation of the date."
    if weekday:
        result = [date.strftime("%a").capitalize()]
    else:
        result = []
    result.append(date.strftime("%d").lstrip("0"))
    result.append(date.strftime("%b"))
    if year and date.year != year:
        result.append(date.strftime("%Y"))
    return " ".join(result)


def date_iso(date):
    return date.strftime("%Y-%m-%d")


def time(datetime):
    "Return representation of the time."
    return datetime.strftime("%H:%M")


def week(date, year=False):
    "Return the week representation for the given date, optionally with the year."
    result = f"v{date.strftime('%V').lstrip('0')}"
    if year:
        result += " " + date.strftime("%Y")
    return result


def get_week(date):
    "Return list of date instances for each of the 7 days following the given."
    return [date] + [date + datetime.timedelta(days=day) for day in range(1, 7)]


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
