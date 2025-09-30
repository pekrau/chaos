"Chaos notebook."

import constants
if constants.DEVELOPMENT:
    from icecream import install
    install()
    ic(constants.DEVELOPMENT)

import os

from fasthtml.common import *

import components
import constants
import entries
import note
import link
import file


entries.read_entry_files()

app, rt = components.get_fast_app(
    routes=[
        Mount("/note", note.app),
        Mount("/link", link.app),
        Mount("/file", file.app),
    ],
)


@rt("/")
def get(auth):
    if auth:
        return (
            Title("chaos"),
            Script(src="/clipboard.min.js"),
            Script("new ClipboardJS('.to_clipboard');"),
            Header(
                Nav(
                    Ul(
                        Li(components.chaos_icon()),
                        Li(components.search_form()),
                        Li(
                            Details(
                                Summary("Add..."),
                                Ul(
                                    Li(A("Note", href="/note/")),
                                    Li(A("Link", href="/link/")),
                                    Li(A("File", href="/file/")),
                                ),
                                cls="dropdown",
                            ),
                        ),
                    ),
                    Ul(
                        Li(
                            A(
                                "Reread",
                                href="/reread",
                                role="button",
                                cls="outline secondary",
                            )
                        ),
                        Li(A("Logout", href="/logout", role="button", cls="outline")),
                    ),
                    style=constants.MAIN_NAV_STYLE,
                ),
                cls="container",
            ),
            Main(
                components.get_entries_table(entries.recent()),
                cls="container",
            ),
            Footer(
                Hr(),
                Div(
                    Div(auth),
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
    return components.redirect("/")


@rt("/logout")
def get(session):
    session.pop("auth", None)
    return components.redirect("/")


@rt("/search")
def get(session, auth, term: str):
    "Search the entries."
    result = []
    for entry in entries.entries_lookup.values():
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
                    Li(
                        Details(
                            Summary("Add..."),
                            Ul(
                                Li(A("Note", href="/note/")),
                                Li(A("Link", href="/link/")),
                                Li(A("File", href="/file/")),
                            ),
                            cls="dropdown",
                        ),
                    ),
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
                Div(auth),
                Div(f"v {constants.VERSION}", style="text-align: right;"),
                cls="grid",
            ),
            cls="container",
        ),
    )


serve(port=5002)
