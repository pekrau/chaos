"Chaos notebook."

from icecream import install

install()

import os
import shutil

import fasthtml
from fasthtml.common import *
import marko
import psutil
import yaml

# This must be done before importing 'constants'.
from dotenv import load_dotenv

load_dotenv()

import components
import constants
import settings
import entries
import note
import link
import file
import image
import listset
import keywords
import api

app, rt = components.get_app_rt(
    routes=[
        Mount("/note", note.app),
        Mount("/link", link.app),
        Mount("/file", file.app),
        Mount("/image", image.app),
        Mount("/listset", listset.app),
        Mount("/keywords", keywords.app),
        Mount("/api", api.app),
    ],
)

settings.read()
entries.read_entries()


@rt("/")
def get(session, page: int = 1):
    if session.get("auth"):
        return components.get_entries_table_page(
            "chaos",
            entries.get_entries(),
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
                                title="chaos: Web service for a repository of notes, links, images and files with no intrinsic order.",
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


@rt("/data/{file:Entry}")
def get(file: entries.Entry):
    "Return the data of the file or image entry."
    assert isinstance(file, entries.GenericFile)
    return Response(
        content=file.filepath.read_bytes(),
        media_type=file.file_mimetype or constants.BINARY_MIMETYPE,
    )


@rt("/notes")
def get(page: int = 1):
    "Display note entries."
    return components.get_entries_table_page(
        "Notes",
        entries.get_entries(entries.Note),
        page,
        "/notes",
    )


@rt("/links")
def get(page: int = 1):
    "Display link entries."
    return components.get_entries_table_page(
        "Links",
        entries.get_entries(entries.Link),
        page,
        "/links",
    )


@rt("/images")
def get(page: int = 1):
    "Display image entries."
    images = entries.get_entries(entries.Image)
    total_entries = len(images)
    images = list(
        images[
            (page - 1) * constants.MAX_PAGE_ENTRIES : page * constants.MAX_PAGE_ENTRIES
        ]
    )
    rows = []
    for chunk in [
        images[i : i + constants.N_GALLERY_ROW_ITEMS]
        for i in range(0, len(images), constants.N_GALLERY_ROW_ITEMS)
    ]:
        row = [
            Div(
                A(
                    Img(src=image.data_url, cls="autoscale display"),
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
            components.get_table_pager(page, total_entries, "/images"),
            cls="container",
        ),
    )


@rt("/files")
def get(page: int = 1):
    "Display file entries."
    return components.get_entries_table_page(
        "Files",
        entries.get_entries(entries.File),
        page,
        "/files",
    )


@rt("/listsets")
def get(page: int = 1):
    "Display listset entries."
    return components.get_entries_table_page(
        "Listsets",
        entries.get_entries(entries.Listset),
        page,
        "/listsets",
    )


@rt("/nokeywords")
def get(page: int = 1):
    "Display entries without keywords."
    return components.get_entries_table_page(
        "No keywords",
        entries.get_no_keyword_entries(),
        page,
        "/nokeywords",
    )


@rt("/unrelated")
def get(page: int = 1):
    "Display entries having no relations."
    return components.get_entries_table_page(
        "Unrelated",
        entries.get_unrelated_entries(),
        page,
        "/unrelated",
    )


@rt("/random")
def get():
    "Display a page of random entries."
    return components.get_entries_table_page(
        "Random",
        entries.get_random_entries(),
        1,
        "/random",
    )


@rt("/search")
def get(term: str, keywords: list[str] = [], type: str = None):
    "Search the entries."
    keywords = set(keywords)
    if type:
        type = type.capitalize()
        if type not in ("Note", "Link", "Image", "File", "Listset"):
            type = None
    result = []
    for entry in entries.lookup.values():
        if type and entry.__class__.__name__ != type:
            continue
        if not keywords.issubset(entry.keywords):
            continue
        if score := entry.score(term):
            if score:
                result.append((score, entry.modified_local, entry))
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
            components.get_entries_table([e for s, m, e in result]),
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
    statistics = entries.get_statistics()
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
                Td("# entries"),
                Td(A(statistics["# entries"], href="/"), cls="right"),
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
                Input(type="submit", value="Reread entries"),
                action="/system/reread",
                method="POST",
            ),
            software,
            cls="container",
        ),
    )


@rt("/system/reread")
def post():
    "Reread all entries from disk."
    settings.read()
    entries.read_entries()
    return components.redirect("/system")


@rt("/logout")
def get(session):
    session.pop("auth", None)
    return components.redirect("/")


serve(port=5002)
