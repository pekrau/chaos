"chaos: Web-based repository of notes, links, images and files with no intrinsic order."

from icecream import install

install()

import os
import shutil
import sys

import fasthtml
from fasthtml.common import *
import marko
import psutil
import yaml

# This must be done before importing 'constants'.
from dotenv import load_dotenv

load_dotenv()
if len(sys.argv) >= 2:
    os.environ["CHAOS_DIR"] = "/home/pekrau/Dropbox/chaos-development"

import components
import constants
import settings
import items
import note
import link
import file
import image
import database
import listset
import keywords
import api

app, rt = components.get_app_rt(
    routes=[
        Mount("/note", note.app),
        Mount("/link", link.app),
        Mount("/file", file.app),
        Mount("/image", image.app),
        Mount("/database", database.app),
        Mount("/listset", listset.app),
        Mount("/keywords", keywords.app),
        Mount("/api", api.app),
    ],
)

settings.read()
items.read_items()


@rt("/")
def get(session, page: int = 1):
    if session.get("auth"):
        return components.get_items_table_page(
            "chaos",
            items.get_items(),
            page,
            "/",
        )
    else:
        return (
            Title("chaos"),
            Header(
                Nav(
                    Ul(
                        Li(
                            A(
                                Img(
                                    src="/chaos.png",
                                    height=24,
                                    width=24,
                                    cls="white",
                                ),
                                title="chaos: Web-based repository of notes, links, images and files with no intrinsic order.",
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
                    components.get_listset_icon(),
                    "Add listset",
                    type="submit",
                    cls="outline",
                ),
                method="GET",
                action="/listset",
            ),
            cls="container",
        ),
    )


@rt("/bin/{file:Item}")
def get(file: items.Item):
    "Return the binary data of the file or image item."
    assert isinstance(file, items.GenericFile)
    return Response(
        content=file.filepath.read_bytes(),
        media_type=file.file_mimetype or constants.BINARY_MIMETYPE,
    )


@rt("/notes")
def get(page: int = 1):
    "Display note items."
    return components.get_items_table_page(
        "Notes",
        items.get_items(items.Note),
        page,
        "/notes",
    )


@rt("/links")
def get(page: int = 1):
    "Display link items."
    return components.get_items_table_page(
        "Links",
        items.get_items(items.Link),
        page,
        "/links",
    )


@rt("/images")
def get(page: int = 1):
    "Display image items."
    images = items.get_items(items.Image)
    total_items = len(images)
    images = list(
        images[(page - 1) * constants.MAX_PAGE_ITEMS : page * constants.MAX_PAGE_ITEMS]
    )
    rows = []
    for chunk in [
        images[i : i + constants.N_GALLERY_ROW_ITEMS]
        for i in range(0, len(images), constants.N_GALLERY_ROW_ITEMS)
    ]:
        row = [
            Div(
                A(
                    Img(src=image.bin_url, cls="autoscale display"),
                    title=image.title,
                    href=str(image.url),
                ),
                components.get_keywords_links(image),
            )
            for image in chunk
        ]
        while len(row) < constants.N_GALLERY_ROW_ITEMS:
            row.append(Div())
        rows.append(Div(*row, cls="grid"))
    return (
        Title("Images"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li("Images"),
                    Li(components.search_form()),
                ),
                cls="main",
            ),
            cls="container",
        ),
        Main(
            *rows,
            components.get_table_pager(page, total_items, "/images"),
            cls="container",
        ),
    )


@rt("/files")
def get(page: int = 1):
    "Display file items."
    return components.get_items_table_page(
        "Files",
        items.get_items(items.File),
        page,
        "/files",
    )


@rt("/databases")
def get(page: int = 1):
    "Display database items."
    return components.get_items_table_page(
        "Databases",
        items.get_items(items.Database),
        page,
        "/databases",
    )


@rt("/listsets")
def get(page: int = 1):
    "Display listset items."
    return components.get_items_table_page(
        "Listsets",
        items.get_items(items.Listset),
        page,
        "/listsets",
    )


@rt("/nokeywords")
def get(page: int = 1):
    "Display items without keywords."
    return components.get_items_table_page(
        "No keywords",
        items.get_no_keyword_items(),
        page,
        "/nokeywords",
    )


@rt("/similar/{item:Item}")
def get(item: items.Item, page: int = 1):
    "Display items similiar to the given item."
    similar = item.similar()
    total_items = len(similar)
    page = min(max(1, page), components.get_total_pages(total_items))
    start = (page - 1) * constants.MAX_PAGE_ITEMS
    end = page * constants.MAX_PAGE_ITEMS
    table = components.get_items_table(similar[start:end])
    pager = components.get_table_pager(page, total_items, f"/similar/{item.id}")
    return (
        Title("Similar items"),
        Script(src="/clipboard.min.js"),
        Script("new ClipboardJS('.to_clipboard');"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li("Similar items"),
                    Li(components.search_form()),
                ),
                cls="main",
            ),
            cls="container",
        ),
        Main(
            Card(components.get_items_table([item])),
            Card(Header("Similar items"), table, Footer(pager)),
            cls="container",
        ),
    )


@rt("/nosimilar")
def get(page: int = 1):
    "Display items having no similarites to any item."
    return components.get_items_table_page(
        "No similar",
        items.get_no_similar_items(),
        page,
        "/nosimilar",
    )


@rt("/random")
def get():
    "Display a page of random items."
    return components.get_items_table_page(
        "Random",
        items.get_random_items(),
        1,
        "/random",
    )


@rt("/search")
def get(term: str, keywords: list[str] = [], type: str = None):
    "Search the items."
    keywords = set(keywords)
    if type:
        type = type.capitalize()
        if type not in ("Note", "Link", "Image", "File", "Listset"):
            type = None
    result = []
    for item in items.lookup.values():
        if type and item.__class__.__name__ != type:
            continue
        if not keywords.issubset(item.keywords):
            continue
        if score := item.score(term):
            if score:
                result.append((score, item.modified_local, item))
    result.sort(key=lambda e: (e[0], e[1]), reverse=True)
    return (
        Title("Search"),
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
                Fieldset(
                    Input(
                        type="text",
                        name="term",
                        placeholder="Term...",
                        value=term or "",
                        autofocus=True,
                    ),
                    Details(
                        Summary("Filter by keywords..."),
                        Ul(
                            *[
                                Li(
                                    Label(
                                        Input(
                                            type="checkbox",
                                            name="keywords",
                                            checked=kw in keywords,
                                            value=kw,
                                        ),
                                        kw,
                                    )
                                )
                                for kw in settings.get_all_keywords()
                            ]
                        ),
                        cls="dropdown",
                    ),
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
                                            checked=t == type,
                                        ),
                                        t,
                                    )
                                )
                                for t in ["Any", "Note", "Link", "Image", "File"]
                            ]
                        ),
                        cls="dropdown",
                    ),
                    Input(type="submit", value="Search"),
                    cls="grid",
                ),
                action="/search",
                method="GET",
            ),
            components.get_items_table([e for s, m, e in result]),
            cls="container",
        ),
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
    statistics = items.get_statistics()
    usage = Table(
        Thead(Tr(Th("Resource usage", Th("Bytes or #", cls="right")))),
        Tbody(
            Tr(
                Td("RAM"),
                Td(
                    components.numerical(psutil.Process().memory_info().rss),
                    cls="right",
                ),
            ),
            Tr(
                Td("Disk"),
                Td(components.numerical(disk_usage), cls="right"),
            ),
            Tr(
                Td("Data directory"),
                Td(constants.DATA_DIR, cls="right"),
            ),
            Tr(
                Td("Disk free"),
                Td(
                    components.numerical(shutil.disk_usage(constants.DATA_DIR).free),
                    cls="right",
                ),
            ),
            Tr(
                Td("# items"),
                Td(A(statistics["# items"], href="/"), cls="right"),
            ),
            Tr(
                Td("# notes"),
                Td(A(statistics["# notes"], href="/notes"), cls="right"),
            ),
            Tr(
                Td("# links"),
                Td(A(statistics["# links"], href="/links"), cls="right"),
            ),
            Tr(
                Td("# images"),
                Td(A(statistics["# images"], href="/images"), cls="right"),
            ),
            Tr(
                Td("# files"),
                Td(A(statistics["# files"], href="/files"), cls="right"),
            ),
            Tr(
                Td("# listsets"),
                Td(A(statistics["# listsets"], href="/listsets"), cls="right"),
            ),
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
    settings.read()
    items.read_items()
    return components.redirect("/system")


@rt("/logout")
def get(session):
    session.pop("auth", None)
    return components.redirect("/")


serve(port=5002)
