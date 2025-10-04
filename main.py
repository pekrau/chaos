"Chaos notebook."

import constants

if constants.DEVELOPMENT:
    from icecream import install

    install()
    ic(constants.DEVELOPMENT)

import os

from fasthtml.common import *
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
    page = max(1, page)
    if session.get("auth"):
        return (
            Title("chaos"),
            Script(src="/clipboard.min.js"),
            Script("new ClipboardJS('.to_clipboard');"),
            Header(
                Nav(
                    Ul(
                        Li(components.chaos_icon()),
                        Li(
                            components.get_dropdown_menu(
                                A("Add note...", href="/note/"),
                                A("Add link...", href="/link/"),
                                A("Add file...", href="/file/"),
                                A("Keywords", href="/keywords"),
                                A("Entries without keywords", href="/nokeywords"),
                                A("Unrelated entries", href="/unrelated"),
                                A("Random entries", href="/random"),
                                A("Reread", href="/reread"),
                                A("Logout", href="/logout"),
                            ),
                        ),
                        Li(components.search_form()),
                    ),
                    cls="main",
                ),
                cls="container",
            ),
            Main(
                components.get_entries_table(
                    entries.get_recent_entries(
                        start=(page - 1) * constants.MAX_PAGE_ENTRIES,
                        end=page * constants.MAX_PAGE_ENTRIES,
                    )
                ),
                components.get_table_pager(page, len(entries.lookup), "/"),
                cls="container",
            ),
            Footer(
                Hr(),
                Small(
                    Div(
                        Div(session["auth"]),
                        Div(
                            A("chaos", href="https://github.com/pekrau/chaos"),
                            " ",
                            constants.VERSION,
                            cls="right",
                        ),
                        cls="grid",
                    ),
                ),
                cls="container",
            ),
        )
    else:
        return (
            Title("chaos"),
            Header(
                Nav(
                    Ul(
                        Li(components.chaos_icon()),
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


@rt("/unrelated")
def get(page: int = 1):
    "Display entries having no relations."
    return (
        Title("Unrelated"),
        Script(src="/clipboard.min.js"),
        Script("new ClipboardJS('.to_clipboard');"),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
                    Li("Unrelated entries"),
                    Li(
                        components.get_dropdown_menu(
                            A("Add note...", href="/note/"),
                            A("Add link...", href="/link/"),
                            A("Add file...", href="/file/"),
                            A("Keywords", href="/keywords"),
                        ),
                    ),
                    Li(components.search_form()),
                ),
                cls="main",
            ),
            cls="container",
        ),
        Main(
            components.get_entries_table(
                entries.get_unrelated_entries(
                    start=(page - 1) * constants.MAX_PAGE_ENTRIES,
                    end=page * constants.MAX_PAGE_ENTRIES,
                )
            ),
            components.get_table_pager(page, len(entries.lookup), "/"),
            cls="container",
        ),
    )


@rt("/nokeywords")
def get(page: int = 1):
    "Display entries without keywords."
    return (
        Title("No keywords"),
        Script(src="/clipboard.min.js"),
        Script("new ClipboardJS('.to_clipboard');"),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
                    Li("Entries without keywords"),
                    Li(
                        components.get_dropdown_menu(
                            A("Add note...", href="/note/"),
                            A("Add link...", href="/link/"),
                            A("Add file...", href="/file/"),
                            A("Keywords", href="/keywords"),
                        ),
                    ),
                    Li(components.search_form()),
                ),
                cls="main",
            ),
            cls="container",
        ),
        Main(
            components.get_entries_table(
                entries.get_no_keyword_entries(
                    start=(page - 1) * constants.MAX_PAGE_ENTRIES,
                    end=page * constants.MAX_PAGE_ENTRIES,
                )
            ),
            components.get_table_pager(page, len(entries.lookup), "/"),
            cls="container",
        ),
    )


@rt("/random")
def get():
    "Display a page of random entries."
    return (
        Title("Random"),
        Script(src="/clipboard.min.js"),
        Script("new ClipboardJS('.to_clipboard');"),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
                    Li("Random entries"),
                    Li(
                        components.get_dropdown_menu(
                            A("Add note...", href="/note/"),
                            A("Add link...", href="/link/"),
                            A("Add file...", href="/file/"),
                            A("Keywords", href="/keywords"),
                        ),
                    ),
                    Li(components.search_form()),
                ),
                cls="main",
            ),
            cls="container",
        ),
        Main(
            components.get_entries_table(entries.get_random_entries()),
            cls="container",
        ),
    )


@rt("/reread")
def get():
    "Reread all entries."
    entries.read_entry_files()
    entries.set_all_keywords_relations()
    return components.redirect("/")


@rt("/logout")
def get(session):
    session.pop("auth", None)
    return components.redirect("/")


@rt("/search")
def get(term: str):
    "Search the entries."
    result = []
    for entry in entries.lookup.values():
        if score := entry.score(term):
            if score:
                result.append((score, entry.modified_local, entry))
    result.sort(reverse=True)
    return (
        Title("Search"),
        Script(src="/clipboard.min.js"),
        Script("new ClipboardJS('.to_clipboard');"),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
                    Li("Search"),
                    Li(
                        components.get_dropdown_menu(
                            A("Add note...", href="/note/"),
                            A("Add link...", href="/link/"),
                            A("Add file...", href="/file/"),
                            A("Keywords", href="/keywords"),
                        ),
                    ),
                    Li(components.search_form(term)),
                ),
                cls="search",
            ),
            cls="container",
        ),
        Main(
            components.get_entries_table([e for s, m, e in result]),
            cls="container",
        ),
    )


@rt("/ping")
def get(request):
    return f"Hello from {request.url}, running chaos v{constants.VERSION}."


serve(port=5002)
