"Chaos notebook."

import constants

if constants.DEVELOPMENT:
    from icecream import install

    install()
    ic(constants.DEVELOPMENT)

import os
import shutil

import fasthtml
from fasthtml.common import *
import marko
import psutil
import yaml

import components
import constants
import settings
import entries
import keywords
import note
import link
import file
import api


settings.read()

entries.read_entry_files()
entries.set_all_keywords_relations()

app, rt = components.get_app_rt(
    routes=[
        Mount("/note", note.app),
        Mount("/link", link.app),
        Mount("/file", file.app),
        Mount("/keywords", keywords.app),
        Mount("/api", api.app),
    ],
)


@rt("/")
def get(session, page: int = 1):
    if session.get("auth"):
        return components.get_entries_table_page(
            session,
            "chaos",
            entries.get_entries(),
            page,
            "/",
            after=components.get_after_buttons(),
        )
    else:
        return (
            Title("chaos"),
            Header(
                Nav(
                    Ul(
                        Li(components.get_chaos_icon()),
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


@rt("/notes")
def get(session, page: int = 1):
    "Display note entries."
    return components.get_entries_table_page(
        session,
        "Notes",
        entries.get_notes(),
        page,
        "/notes",
        after=components.get_after_buttons(),
    )


@rt("/links")
def get(session, page: int = 1):
    "Display note entries."
    return components.get_entries_table_page(
        session,
        "Links",
        entries.get_links(),
        page,
        "/links",
        after=components.get_after_buttons(),
    )


@rt("/files")
def get(session, page: int = 1):
    "Display note entries."
    return components.get_entries_table_page(
        session,
        "Files",
        entries.get_files(),
        page,
        "/files",
        after=components.get_after_buttons(),
    )


@rt("/nokeywords")
def get(session, page: int = 1):
    "Display entries without keywords."
    return components.get_entries_table_page(
        session,
        "No keywords",
        entries.get_no_keyword_entries(),
        page,
        "/nokeywords",
        after=components.get_after_buttons(),
    )


@rt("/unrelated")
def get(session, page: int = 1):
    "Display entries having no relations."
    return components.get_entries_table_page(
        session,
        "Unrelated",
        entries.get_unrelated_entries(),
        page,
        "/unrelated",
        after=components.get_after_buttons(),
    )


@rt("/random")
def get(session):
    "Display a page of random entries."
    return components.get_entries_table_page(
        session,
        "Random",
        entries.get_random_entries(),
        1,
        "/random",
        after=components.get_after_buttons(),
    )


@rt("/search")
def get(term: str, keywords: list[str] = []):
    "Search the entries."
    keywords = set(keywords)
    result = []
    for entry in entries.lookup.values():
        if not keywords.issubset(entry.keywords):
            continue
        if score := entry.score(term):
            if score:
                result.append((score, entry.modified_local, entry))
    result.sort(key=lambda e: (-e[0], e[1]), reverse=True)
    return (
        Title("Search"),
        Header(
            Nav(
                Ul(
                    Li(components.get_chaos_icon()),
                    Li("Search"),
                    Li(components.get_nav_menu()),
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
                        Summary("Keywords..."),
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
                                for kw in sorted(settings.canonical_keywords)
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
            components.get_after_buttons(),
            cls="container",
        ),
    )


@rt("/system")
def get():
    "Displaysystem information."
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
    disk_usage = 0
    for dirpath, dirnames, filenames in os.walk(constants.DATA_DIR):
        dp = Path(dirpath)
        for filename in filenames:
            fp = dp / filename
            disk_usage += os.path.getsize(fp)
    usage = Table(
        Thead(Tr(Th("System usage", Th("Bytes", cls="right")))),
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
                Td("Disk free"),
                Td(
                    components.numerical(shutil.disk_usage(constants.DATA_DIR).free),
                    cls="right",
                ),
            ),
        ),
    )
    return (
        Title("System"),
        Header(
            Nav(
                Ul(
                    Li(components.get_chaos_icon()),
                    Li("System"),
                ),
                cls="main",
            ),
            cls="container",
        ),
        Main(software, usage, components.get_after_buttons(), cls="container"),
    )


@rt("/ping")
def get(request):
    return f"Hello from {request.url}, running chaos v{constants.__version__}."


@rt("/logout")
def get(session):
    session.pop("auth", None)
    return components.redirect("/")


serve(port=5002)
