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


settings.read()

entries.read_entry_files()
entries.set_all_keywords_relations()

app, rt = components.get_fast_app(
    routes=[
        Mount("/note", note.app),
        Mount("/link", link.app),
        Mount("/file", file.app),
        Mount("/keywords", keywords.app),
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
                            Details(
                                Summary("Actions..."),
                                Ul(
                                    Li(A("Add note...", href="/note")),
                                    Li(A("Add link...", href="/link")),
                                    Li(A("Add file...", href="/file")),
                                    Li(A("Reread", href="/reread")),
                                    Li(A("Logout", href="/logout")),
                                ),
                                cls="dropdown",
                            ),
                        ),
                        Li(
                            A(
                                "Keywords",
                                href="/keywords",
                                role="button",
                            )
                        ),
                        Li(components.search_form()),
                    ),
                    style=constants.MAIN_NAV_STYLE,
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
                Div(
                    Div(session["auth"]),
                    Div(f"v {constants.VERSION}", style="text-align: right;"),
                    cls="grid",
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
                    style=constants.LOGIN_NAV_STYLE,
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
            Footer(
                Hr(),
                Div(f"v {constants.VERSION}", style="text-align: right;"),
                cls="container",
            ),
        )


@rt("/")
def post(session, username: str, password: str):
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


@rt("/reread")
def get(session):
    "Reread all entries."
    entries.read_entry_files()
    entries.set_all_keywords_relations()
    return components.redirect("/")


@rt("/logout")
def get(session):
    session.pop("auth", None)
    return components.redirect("/")


@rt("/search")
def get(session, term: str):
    "Search the entries."
    result = []
    for entry in entries.lookup.values():
        if score := entry.score(term):
            if score:
                result.append((score, entry.modified_local, entry))
    result.sort(reverse=True)
    return (
        Title("chaos"),
        Script(src="/clipboard.min.js"),
        Script("new ClipboardJS('.to_clipboard');"),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
                    Li("Search"),
                    Li(components.search_form(term)),
                ),
                Ul(
                    Li(components.get_add_dropdown()),
                ),
                style=constants.SEARCH_NAV_STYLE,
            ),
            cls="container",
        ),
        Main(
            components.get_entries_table([e for s, m, e in result]),
            cls="container",
        ),
        Footer(
            Hr(),
            Div(
                Div(session["auth"]),
                Div(f"v {constants.VERSION}", style="text-align: right;"),
                cls="grid",
            ),
            cls="container",
        ),
    )


serve(port=5002)
