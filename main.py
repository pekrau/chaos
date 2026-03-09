"chaos: Web-based repository of notes, links, images and files with no intrinsic order."

from icecream import install

install()

import os
import shutil
import sys

import bokeh
import fasthtml
from fasthtml.common import *
import marko
import numpy
import psutil
import yaml

# This must be done before importing 'constants'.
from dotenv import load_dotenv

load_dotenv()
if os.environ.get("CHAOS_DEVELOPMENT"):
    os.environ["CHAOS_DIR"] = "/home/pekrau/Dropbox/chaos-development"

import components
import constants
import errors
import items
import note
import link
import file
import image
import database
import graphic
import api
import utils

app, rt = components.get_app_rt(
    routes=[
        Mount("/note", note.app),
        Mount("/link", link.app),
        Mount("/file", file.app),
        Mount("/image", image.app),
        Mount("/database", database.app),
        Mount("/graphic", graphic.app),
        Mount("/api", api.app),
    ]
)

items.read_items()


@rt("/")
def get(session, page: int = 1):
    if session.get("auth"):
        result = items.get_items()
        total_items = len(result)
        page = min(max(1, page), utils.get_total_pages(total_items))
        start = (page - 1) * constants.MAX_PAGE_ITEMS
        end = page * constants.MAX_PAGE_ITEMS
        result = result[start:end]
        title = "chaos"
        return (
            Title(title),
            components.clipboard_script(),
            Header(
                Nav(
                    Ul(
                        Li(components.get_nav_menu()),
                        Li(title),
                    ),
                    Ul(
                        Li(
                            Form(
                                Input(
                                    type="search",
                                    name="term",
                                    placeholder="Search...",
                                    aria_label="Search",
                                ),
                                cls="search",
                                role="search",
                                action="/search",
                                method="GET",
                            ),
                        ),
                    ),
                ),
                cls="container",
            ),
            Main(
                components.get_items_list(result),
                Form(
                    components.get_items_display_pager(page, total_items),
                    method="GET",
                    action="/",
                ),
                cls="container",
            ),
            components.clipboard_activate(),
        )

    else:
        return (
            Title("chaos"),
            Header(
                Nav(
                    Ul(
                        Li(
                            A(
                                components.get_chaos_icon(),
                                role="button",
                                cls="secondary outline nomargin",
                                href="/",
                            )
                        ),
                        Li("Login"),
                    ),
                    cls="login",
                ),
                cls="container",
            ),
            Main(
                Div(
                    Div(
                        Form(
                            Input(
                                type="text",
                                name="username",
                                placeholder="User name...",
                                autofocus=True,
                                required=True,
                            ),
                            Input(
                                type="password",
                                name="password",
                                placeholder="Password...",
                                required=True,
                            ),
                            Input(type="submit", value="Login"),
                            action="/",
                            method="POST",
                        ),
                        Div(),
                        cls="grid",
                    ),
                ),
                cls="container",
            ),
        )


@rt("/")
def post(session, username: str, password: str):
    "Actually perform login."
    if not username or not password:
        add_toast(session, "Missing username and/or password.", "error")
        return components.redirect("/")
    try:
        if username != os.environ.get("CHAOS_USERNAME"):
            raise KeyError
        if password != os.environ.get("CHAOS_PASSWORD"):
            raise KeyError
    except KeyError:
        add_toast(session, "Invalid username and/or password.", "error")
        return components.redirect("/")
    session["auth"] = username
    return components.redirect(session.pop("path", None) or "/")


@rt("/data/{item:Item}.{ext:Ext}")
def get(item: items.Item, ext: str):
    return f"{item} {ext}"


@rt("/static/{filename:path}")
async def get(filename: str):
    """Replacement of the default static response handler.
    Required since the 'static' convertor has been made useless, which
    in turn was needed to enable using file extensions for determining
    format of the data content for '/data' resources. The
    predefined 'static' convertor somehow prevented this.
    """
    return FileResponse(f"static/{filename}")


@rt("/add")
def get():
    "Page for selecting type of item to add."
    return (
        Title("Add item..."),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li("Add item..."),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                Button(
                    components.get_note_icon(),
                    "Add note",
                    type="submit",
                    cls="outline",
                ),
                method="GET",
                action="/note",
            ),
            Form(
                Button(
                    components.get_link_icon(),
                    "Add link",
                    type="submit",
                    cls="outline",
                ),
                method="GET",
                action="/link",
            ),
            Form(
                Button(
                    components.get_image_icon(),
                    "Add image",
                    type="submit",
                    cls="outline",
                ),
                method="GET",
                action="/image",
            ),
            Form(
                Button(
                    components.get_file_icon(),
                    "Add file",
                    type="submit",
                    cls="outline",
                ),
                method="GET",
                action="/file",
            ),
            Form(
                Button(
                    components.get_database_icon(),
                    "Add database",
                    type="submit",
                    cls="outline",
                ),
                method="GET",
                action="/database",
            ),
            Form(
                Button(
                    components.get_graphic_icon(),
                    "Add graphic",
                    type="submit",
                    cls="outline",
                ),
                method="GET",
                action="/graphic",
            ),
            cls="container",
        ),
    )


@rt("/search")
def get(term: str = None, type: str = "", display: str = "list", page: int = 1):
    "Search the items."
    if type:
        type = type.capitalize()
        if type not in constants.TYPES:
            type = ""
    result = []
    if type:
        if term:
            for item in items.get_items(type):
                if score := item.score(term):
                    result.append((score, item.modified_local, item))
        else:
            for item in items.get_items(type):
                result.append((1.0, item.modified_local, item))
    elif term:
        for item in items.get_items():
            if score := item.score(term):
                result.append((score, item.modified_local, item))
    if type not in constants.TYPES:
        type = "Any"

    total_items = len(result)
    result.sort(key=lambda e: (e[0], e[1]), reverse=True)
    page = min(max(1, page), utils.get_total_pages(total_items))
    start = (page - 1) * constants.MAX_PAGE_ITEMS
    end = page * constants.MAX_PAGE_ITEMS
    result = [i for s, m, i in result[start:end]]

    return (
        Title("Search"),
        components.clipboard_script(),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li("Search"),
                ),
                cls="search",
            ),
            cls="container",
        ),
        Main(
            Form(
                Input(
                    type="text",
                    name="term",
                    placeholder="Search...",
                    value=term or "",
                    autofocus=True,
                ),
                Fieldset(
                    Details(
                        Summary("Select type..."),
                        Ul(
                            *[
                                Li(
                                    Label(
                                        Input(
                                            type="radio",
                                            name="type",
                                            value=t,
                                            checked=t == type,
                                        ),
                                        t,
                                    )
                                )
                                for t in ["Any"] + constants.TYPES
                            ]
                        ),
                        cls="dropdown",
                    ),
                    Select(
                        Option(
                            "List display", value="list", selected=display == "list"
                        ),
                        Option(
                            "Gallery display",
                            value="gallery",
                            selected=display == "gallery",
                        ),
                        name="display",
                    ),
                    Input(type="submit", value="Search"),
                    cls="grid",
                ),
                components.get_items_display(result, gallery=display == "gallery"),
                components.get_items_display_pager(page, total_items),
                action="/search",
                method="GET",
            ),
            cls="container",
        ),
        components.clipboard_activate(),
    )


@rt("/system")
def get():
    "Display system information."
    disk_usage = 0
    for dirpath, dirnames, filenames in os.walk(constants.DATA_DIR):
        dp = Path(dirpath)
        for filename in filenames:
            fp = dp / filename
            disk_usage += os.path.getsize(fp)
    disk_free = shutil.disk_usage(constants.DATA_DIR).free
    statistics = items.get_statistics()
    usage = Table(
        Thead(Tr(Th("Resource usage", Th("Bytes or #", cls="right")))),
        Tbody(
            Tr(
                Td("RAM"),
                Td(
                    utils.numerical(psutil.Process().memory_info().rss),
                    cls="right",
                ),
            ),
            Tr(
                Td("Data directory"),
                Td(constants.DATA_DIR, cls="right"),
            ),
            Tr(
                Td("Disk usage"),
                Td(
                    utils.numerical(disk_usage),
                    Span(
                        f"{100 * disk_usage / (disk_usage + disk_free):.1f}%",
                        style="margin-left: 2em;",
                    ),
                    cls="right",
                ),
            ),
            Tr(
                Td("Disk free"),
                Td(
                    utils.numerical(disk_free),
                    Span(
                        f"{100 * disk_free / (disk_usage + disk_free):.1f}%",
                        style="margin-left: 2em;",
                    ),
                    cls="right",
                ),
            ),
            *[
                Tr(
                    Td(f"# {key}s"),
                    Td(A(statistics[key], href=f"/{key}s"), cls="right"),
                )
                for key in statistics
            ],
        ),
    )
    software = Table(
        Thead(Tr(Th("Software", Th("Version", cls="right")))),
        Tbody(
            Tr(
                Td(A("chaos", href=constants.GITHUB_URL)),
                Td(constants.__version__, cls="right"),
            ),
            Tr(
                Td(A("Python", href="https://www.python.org/")),
                Td(f"{'.'.join([str(v) for v in sys.version_info[0:3]])}", cls="right"),
            ),
            Tr(
                Td(A("fastHTML", href="https://fastht.ml/")),
                Td(fasthtml.__version__, cls="right"),
            ),
            Tr(
                Td(A("Marko", href="https://marko-py.readthedocs.io/")),
                Td(marko.__version__, cls="right"),
            ),
            Tr(
                Td(A("PyYAML", href="https://pypi.org/project/PyYAML/")),
                Td(yaml.__version__, cls="right"),
            ),
            Tr(
                Td(A("bokeh", href="https://bokeh.org/")),
                Td(bokeh.__version__, cls="right"),
            ),
            Tr(
                Td(A("NumPy", href="https://numpy.org/")),
                Td(numpy.__version__, cls="right"),
            ),
        ),
    )
    return (
        Title("System"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li("System"),
                ),
                cls="main",
            ),
            cls="container",
        ),
        Main(
            usage,
            Form(
                Input(type="submit", value="Reread items"),
                action="/system/reread",
                method="POST",
            ),
            software,
            cls="container",
        ),
    )


@rt("/system/reread")
def post():
    "Reread all items from disk."
    items.read_items()
    return components.redirect("/system")


@rt("/logout")
def get(session):
    session.pop("auth", None)
    return components.redirect("/")


serve(port=5002)
