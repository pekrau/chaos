"Various utility functions."

import datetime as dt
import os
import os.path
import shutil
import sys
import unicodedata

import bibtexparser
import click
import fasthtml
import marko
import psutil
import requests
import webcolors
import yaml

import constants


def iso_utc_from_timestamp(timestamp):
    "Convert timestamp to ISO format string in UTC timezone."
    return dt.datetime.fromtimestamp(timestamp, tz=dt.UTC).strftime("%Y-%m-%d %H:%M:%S")


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
    "Convert to name color, or keep in hex if no name."
    if not color:
        return color
    if color.startswith("#"):
        try:
            color = webcolors.hex_to_name(webcolors.normalize_hex(color))
        except ValueError:
            pass
    return color


def get_total_pages(total_items):
    "Return the total number of table pages for the given number of items."
    return (total_items - 1) // constants.MAX_PAGE_ITEMS + 1


def get_status():
    "Get the status of the instance: resources, item counts, software"
    import items

    ram = psutil.virtual_memory()
    disk = psutil.disk_usage(constants.DATA_DIR)
    resources = {
        "ram_total": ram.total,
        "ram_free": ram.free,
        "ram_used": ram.used,
        "ram_process": psutil.Process().memory_info().rss,
        "disk_total": disk.total,
        "disk_free": disk.free,
        # This sums sizes of all files, not just '.md' files.
        "disk_data": sum(
            [
                os.path.getsize(constants.DATA_DIR / filename)
                for filename in constants.DATA_DIR.iterdir()
            ]
        ),
        "disk_percent": disk.percent,
        "items_count": len(items.lookup),
        "trash_count": len(
            [
                filename
                for filename in constants.TRASH_DIR.iterdir()
                if not filename.suffix
            ]
        ),
        "trash_used": sum(
            [
                os.path.getsize(constants.TRASH_DIR / filename)
                for filename in constants.TRASH_DIR.iterdir()
            ]
        ),
    }
    resources["ram_percent"] = 100 * resources["ram_process"] / ram.total
    resources["disk_percent"] = 100 * resources["disk_data"] / disk.total
    software = [
        dict(name="chaos", href=constants.GITHUB_URL, version=constants.__version__),
        dict(
            name="Python",
            href="https://www.python.org/",
            version=".".join([str(v) for v in sys.version_info[0:3]]),
        ),
        dict(name="fastHTML", href="https://fastht.ml/", version=fasthtml.__version__),
        dict(
            name="Marko",
            href="https://marko-py.readthedocs.io/",
            version=marko.__version__,
        ),
        dict(
            name="PyYAML",
            href="https://pypi.org/project/PyYAML/",
            version=yaml.__version__,
        ),
        dict(
            name="BibtexParser",
            href="https://bibtexparser.readthedocs.io/en/main/",
            version=bibtexparser.__version__,
        ),
        dict(
            name="requests",
            href="https://requests.readthedocs.io/en/latest/",
            version=requests.__version__,
        ),
        dict(
            name="click",
            href="https://click.palletsprojects.com/en/stable/",
            version=click.__version__,
        ),
        dict(
            name="psutil",
            href="https://github.com/giampaolo/psutil",
            version=psutil.__version__,
        ),
        dict(
            name="webcolors",
            href="https://webcolors.readthedocs.io/en/stable/",
            version=constants.WEBCOLORS_VERSION,
        ),
        dict(
            name="Tabulator",
            href="https://tabulator.info/",
            version=constants.TABULATOR_VERSION,
        ),
    ]
    return dict(
        version=constants.__version__,
        resources=resources,
        data_items=items.get_counts(),
        software=software,
    )
