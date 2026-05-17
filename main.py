"""chaos: Web-based personal repository of notes, tags, links, images, files,
databases, graphics, books and articles.
"""

import itertools
import locale
import os
import shutil
import sys

import bibtexparser
import fasthtml
from fasthtml.common import *
import icecream
import marko
import psutil
import yaml

icecream.install()

# This must be done before importing 'constants'.
from dotenv import load_dotenv

if os.environ.get("CHAOS_DEVELOPMENT"):
    with open(".env-development") as infile:
        load_dotenv(stream=infile)
else:
    load_dotenv()


import bibtex
import components
import constants
import items
import note
import tag
import link
import event
import file
import image
import database
import graphic
import book
import article
import api
import utils

locale.setlocale(locale.LC_ALL, "")

app, rt = components.get_app_rt(
    routes=[
        Mount("/note", note.app),
        Mount("/tag", tag.app),
        Mount("/link", link.app),
        Mount("/event", event.app),
        Mount("/file", file.app),
        Mount("/image", image.app),
        Mount("/database", database.app),
        Mount("/graphic", graphic.app),
        Mount("/book", book.app),
        Mount("/article", article.app),
        Mount("/api", api.app),
    ]
)

items.read()


@rt("/")
def get(page: int = 1):
    "Display all items; paged."
    result = items.get_items()
    result.sort(key=lambda i: i.modified, reverse=True)
    title = "chaos"
    return (
        Title(title),
        components.get_clipboard_script(),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(Strong(title)),
                ),
                Ul(
                    Li(components.get_search()),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                components.get_items_display(result, page=page),
                action="/",
            ),
            cls="container",
        ),
        components.get_clipboard_activate(),
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
def post(session, password: str):
    "Actually perform login."
    if not password:
        add_toast(session, "Missing password.", "error")
        return components.redirect("/login")
    try:
        if password != os.environ.get("CHAOS_PASSWORD"):
            raise KeyError
    except KeyError:
        add_toast(session, "Invalid password.", "error")
        return components.redirect("/login")
    session["auth"] = "logged in"
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
    forms = [
        Form(
            Button(
                components.get_type_icon(type),
                f"Add {type}",
                type="submit",
                cls="outline",
            ),
            action=f"/{type.lower()}",
        )
        for type in items.TYPES
    ]
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
            *[Div(*t, cls="grid") for t in itertools.batched(forms, 2)], cls="container"
        ),
    )


@rt("/search")
def get(
    term: str = None,
    type: str = "",
    tags: list[str] = None,
    display: str = "",
    order: str = "",
    page: int = 1,
):
    "Search among the items."
    # Filter by item type.
    if type in items.TYPES:
        # Filter by tags.
        if tags:
            candidates = (
                i
                for i in items.lookup.values()
                if i.type == type and i.tag_ids.intersection(tags)
            )
        else:
            candidates = (i for i in items.lookup.values() if i.type == type)

    # Filter by tags.
    elif tags:
        candidates = (i for i in items.lookup.values() if i.tag_ids.intersection(tags))
    # No filter.
    else:
        candidates = None

    result = []
    # Search by term.
    if term:
        if candidates is None:
            candidates = items.lookup.values()
        for item in candidates:
            if score := item.score(term):
                item._score = score
                result.append(item)

    # No term; all filtered items.
    elif candidates is not None:
        result = list(candidates)
        for item in result:
            item._score = 0

    # Sort the resulting items.
    match order:
        case "term_desc":
            if term:
                result.sort(key=lambda i: (i._score, i.modified), reverse=True)
            else:
                result.sort(key=lambda i: item.modified, reverse=True)
        case "age_asc":
            result.sort(key=lambda i: i.modified, reverse=True)
        case "age_desc":
            result.sort(key=lambda i: i.modified)
        case "lex_asc":
            result.sort(key=lambda i: i.title.casefold())
        case "lex_desc":
            result.sort(key=lambda i: i.title.casefold(), reverse=True)
        case _:
            if term:
                result.sort(key=lambda i: (i._score, i.modified), reverse=True)
            else:
                result.sort(key=lambda i: i.modified, reverse=True)

    return (
        Title("Search"),
        components.get_clipboard_script(),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li("Search"),
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
                    Details(
                        Summary("Filter by type..."),
                        Ul(
                            *[
                                Li(
                                    Label(
                                        Input(
                                            type="radio",
                                            name="type",
                                            value=t,
                                            checked=t == type
                                            or (t == "Any" and not type),
                                        ),
                                        t.capitalize(),
                                    )
                                )
                                for t in ["Any"] + list(items.TYPES)
                            ]
                        ),
                        cls="dropdown",
                    ),
                    Details(
                        Summary("Filter by tags..."),
                        Ul(
                            *[
                                Li(
                                    Label(
                                        Input(
                                            type="checkbox",
                                            name="tags",
                                            value=t.id,
                                            checked=t.id in tags,
                                        ),
                                        t.title,
                                    )
                                )
                                for t in items.get_items(
                                    type="tag", key=lambda t: t.title.casefold()
                                )
                            ]
                        ),
                        cls="dropdown",
                    ),
                    Details(
                        Summary("Order by..."),
                        Ul(
                            Li(
                                Label(
                                    Input(
                                        type="radio",
                                        name="order",
                                        value="term_desc",
                                        checked=order == "term_desc" or not order,
                                    ),
                                    "Term score, descending",
                                )
                            ),
                            Li(
                                Label(
                                    Input(
                                        type="radio",
                                        name="order",
                                        value="age_asc",
                                        checked=order == "age_asc",
                                    ),
                                    "Age, ascending",
                                )
                            ),
                            Li(
                                Label(
                                    Input(
                                        type="radio",
                                        name="order",
                                        value="age_desc",
                                        checked=order == "age_desc",
                                    ),
                                    "Age, descending",
                                )
                            ),
                            Li(
                                Label(
                                    Input(
                                        type="radio",
                                        name="order",
                                        value="lex_asc",
                                        checked=order == "lex_asc",
                                    ),
                                    "Lexicographically, ascending",
                                )
                            ),
                            Li(
                                Label(
                                    Input(
                                        type="radio",
                                        name="order",
                                        value="lex_desc",
                                        checked=order == "lex_desc",
                                    ),
                                    "Lexicographically, descending",
                                )
                            ),
                        ),
                        cls="dropdown",
                    ),
                    Fieldset(
                        Label(
                            Input(
                                type="radio",
                                name="display",
                                value="list",
                                checked=display == "list" or not display,
                            ),
                            "List",
                        ),
                        Label(
                            Input(
                                type="radio",
                                name="display",
                                value="gallery",
                                checked=display == "gallery",
                            ),
                            "Gallery",
                        ),
                    ),
                    Input(type="submit", value="Search"),
                    cls="grid",
                ),
                components.get_items_display(
                    result,
                    title="Search results",
                    page=page,
                    gallery=display.lower() == "gallery",
                ),
                action="/search",
            ),
            cls="container",
        ),
        components.get_clipboard_activate(),
    )


@rt("/pin/{item:Item}")
def get(item: items.Item):
    "Pin this item to the shortcuts menu."
    items.write_state(pin=item)
    return components.redirect(item.url)


@rt("/unpin/{item:Item}")
def get(item: items.Item):
    "Remove this item from the shortcuts menu."
    items.write_state(unpin=item)
    return components.redirect(item.url)


@rt("/source/{item:Item}")
def get(item: items.Item):
    return Response(content=item.path.read_text(), media_type=constants.TEXT_MIMETYPE)


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
        Thead(Tr(Th("Resource usage", colspan=2))),
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
            Tr(
                Td("# items"),
                Td(A(statistics.pop("item"), href="/search"), cls="right"),
            ),
            *[
                Tr(
                    Td(f"# {key}s"),
                    Td(A(statistics[key], href=f"/search?type={key}"), cls="right"),
                )
                for key in statistics
            ],
        ),
    )
    software = Table(
        Thead(
            Tr(
                Th(A("chaos", href=constants.GITHUB_URL, target="_blank")),
                Th(constants.__version__, cls="right"),
            ),
        ),
        Tbody(
            Tr(
                Td(A("Python", href="https://www.python.org/", target="_blank")),
                Td(f"{'.'.join([str(v) for v in sys.version_info[0:3]])}", cls="right"),
            ),
            Tr(
                Td(A("fastHTML", href="https://fastht.ml/", target="_blank")),
                Td(fasthtml.__version__, cls="right"),
            ),
            Tr(
                Td(
                    A("Marko", href="https://marko-py.readthedocs.io/", target="_blank")
                ),
                Td(marko.__version__, cls="right"),
            ),
            Tr(
                Td(
                    A(
                        "PyYAML",
                        href="https://pypi.org/project/PyYAML/",
                        target="_blank",
                    )
                ),
                Td(yaml.__version__, cls="right"),
            ),
            Tr(
                Td(
                    A(
                        "BibtexParser",
                        href="https://bibtexparser.readthedocs.io/en/main/",
                        target="_blank",
                    )
                ),
                Td(bibtexparser.__version__, cls="right"),
            ),
            Tr(
                Td(A("Tabulator", href="https://tabulator.info/", target="_blank")),
                Td(constants.TABULATOR_VERSION, cls="right"),
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
                Ul(
                    Li(components.get_search()),
                ),
                cls="main",
            ),
            cls="container",
        ),
        Main(
            usage,
            software,
            Div(
                Form(
                    Input(type="submit", value="Reread items"),
                    action="/system/reread",
                    method="POST",
                ),
                Form(
                    Input(type="submit", value="Logout"),
                    action="/logout",
                    method="POST",
                ),
                cls="grid",
            ),
            cls="container",
        ),
    )


@rt("/system/reread")
def post():
    "Reread all items from disk."
    items.read()
    return components.redirect()


@rt("/logout")
def post(session):
    session.pop("auth", None)
    return components.redirect()


serve(port=5002)
