"chaos: Web-based repository of notes, links, images, files, graphics and databases."

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

items.read()


@rt("/")
def get(session, page: int = 1):
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
                    Li(components.get_shortcuts_menu(session)),
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


@rt("/login")
def get():
    "Form for logging in."
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
                        action="/login",
                        method="POST",
                    ),
                    Div(),
                    cls="grid",
                ),
            ),
            cls="container",
        ),
    )


@rt("/login")
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


@rt("/static/{filename:path}")
async def get(filename: str):
    """Replacement of the default static response handler.
    Required since the 'static' convertor has been made useless, which
    in turn was needed to enable using file extensions for determining
    format of the data content for different items. The predefined
    'static' convertor somehow prevented this.
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
def get(
    session,
    term: str = None,
    type: str = "",
    display: str = "",
    order: str = "",
    page: int = 1,
):
    "Search the items."
    if type:
        type = type.capitalize()
        if type not in constants.TYPES:
            type = ""

    # Filter by type.
    if type:
        # Items with a non-zero score.
        if term:
            result = []
            for item in items.get_items(type):
                if score := item.score(term):
                    result.append((score, item))
        # All items of the type.
        else:
            result = [(0, i) for i in items.get_items(type)]

    # Items with a non-zero score.
    elif term:
        result = []
        for item in items.get_items():
            if score := item.score(term):
                result.append((score, item))

    # Neither type nor term specified; no result.
    else:
        result = []

    match order:
        case "term_desc":
            if term:
                result.sort(key=lambda t: (t[0], t[1].modified), reverse=True)
            else:
                result.sort(key=lambda t: t[1].modified, reverse=True)
        case "age_asc":
            result.sort(key=lambda t: t[1].modified, reverse=True)
        case "age_desc":
            result.sort(key=lambda t: t[1].modified)
        case "cnx_asc":
            result.sort(key=lambda t: (-t[1].n_xrefs, t[1].modified), reverse=True)
        case "cnx_desc":
            result.sort(key=lambda t: (t[1].n_xrefs, t[1].modified), reverse=True)
        case _:
            if term:
                result.sort(key=lambda t: (t[0], t[1].modified), reverse=True)
            else:
                result.sort(key=lambda t: t[1].modified, reverse=True)

    total_items = len(result)
    page = min(max(1, page), utils.get_total_pages(total_items))
    start = (page - 1) * constants.MAX_PAGE_ITEMS
    end = page * constants.MAX_PAGE_ITEMS
    result = [i for s, i in result[start:end]]

    display = display.lower()
    if display == "gallery":
        rows = []
        for chunk in [
            result[i : i + constants.N_GALLERY_ROW_ITEMS]
            for i in range(0, len(result), constants.N_GALLERY_ROW_ITEMS)
        ]:
            row = []
            for item in chunk:
                if item.type == "image":
                    row.append(
                        Div(
                            A(
                                components.get_image_icon(),
                                item.title,
                                Img(src=item.url_file, cls="autoscale display"),
                                href=str(item.url),
                            ),
                        )
                    )
                else:
                    row.append(Div(components.get_item_link(item)))
            while len(row) < constants.N_GALLERY_ROW_ITEMS:
                row.append(Div())
            rows.append(Div(*row, cls="bottom grid", style="margin-bottom: 1em;"))
    else:
        rows = components.get_items_list_rows(result)

    if rows:
        items_display = Table(Tbody(*rows), cls="compressed")
    else:
        items_display = I("No items.")

    return (
        Title("Search"),
        components.clipboard_script(),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li("Search"),
                ),
                Ul(
                    Li(components.get_shortcuts_menu(session)),
                ),
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
                ),
                Fieldset(
                    Select(
                        Option("Filter by type...", disabled=True, selected=True),
                        *[
                            Option(t, selected=t == type)
                            for t in ["Any"] + constants.TYPES
                        ],
                        name="type",
                    ),
                    Select(
                        Option("Display...", disabled=True, selected=True),
                        Option("List", selected=display == "list"),
                        Option("Gallery", selected=display == "gallery"),
                        name="display",
                    ),
                    Select(
                        Option("Order by...", disabled=True, selected=True),
                        Option(
                            "Term score, descending",
                            value="term_desc",
                            selected=order == "term_desc",
                        ),
                        Option(
                            "Age, ascending",
                            value="age_asc",
                            selected=order == "age_asc",
                        ),
                        Option(
                            "Age, descending",
                            value="age_desc",
                            selected=order == "age_desc",
                        ),
                        Option(
                            "Connectivity, ascending",
                            value="cnx_asc",
                            selected=order == "cnx_asc",
                        ),
                        Option(
                            "Connectivity, descending",
                            value="cnx_desc",
                            selected=order == "cnx_desc",
                        ),
                        name="order",
                    ),
                    Input(type="submit", value="Search"),
                    cls="grid",
                ),
                items_display,
                components.get_items_display_pager(page, total_items),
                action="/search",
                method="GET",
            ),
            cls="container",
        ),
        components.clipboard_activate(),
    )


@rt("/pin/{item:Item}")
def get(item: items.Item):
    "Pin this item to the shortcuts menu."
    item.pin()
    return components.redirect(item.url)


@rt("/unpin/{item:Item}")
def get(item: items.Item):
    "Remove this item from the shortcuts menu."
    item.unpin()
    return components.redirect(item.url)


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
    items.read()
    return components.redirect("/system")


@rt("/logout")
def get(session):
    session.pop("auth", None)
    return components.redirect("/")


serve(port=5002)
