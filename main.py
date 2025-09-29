"Chaos notebook."

from icecream import install

install()

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
                                    Li(A("Note", href="/note")),
                                    Li(A("Link", href="/link")),
                                    Li(A("File", href="/file")),
                                ),
                                cls="dropdown",
                            ),
                        ),
                    ),
                    Ul(
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
                    style=constants.MAIN_NAV_STYLE,
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
    return components.redirect(session.pop("path") or "/")


@rt("/logout")
def get(session):
    session.pop("auth", None)
    return components.redirect("/")


@rt("/search")
def get(session):
    "Search the entries."
    raise NotImplementedError


serve(port=5002)
