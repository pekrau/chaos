"Components for output generation."

from http import HTTPStatus as HTTP

from fasthtml.common import *

import constants


class Error(Exception):
    "Custom exception; return response with message and status code."

    def __init__(self, message, status_code=HTTP.BAD_REQUEST):
        super().__init__(message)
        self.status_code = status_code


def error_handler(request, exc):
    "Return a response with the message and status code."
    return Response(content=str(exc), status_code=exc.status_code)


def set_auth_before(request, session):
    auth = session.get("auth", None)
    if auth:
        request.scope["auth"] = auth
    elif request.url.path != "/":
        add_toast(session, "Login required.", "error")
        session["path"] = request.url.path
        return redirect("/")


def get_fast_app(routes=None):
    app, rt = fast_app(
        live="CHAOS_DEVELOPMENT" in os.environ,
        static_path="static",
        before=set_auth_before,
        hdrs=(Link(rel="stylesheet", href="/mods.css", type="text/css"),),
        exception_handlers={
            Error: error_handler,
        },
        routes=routes,
    )
    setup_toasts(app)
    return app, rt


def redirect(href):
    "Redirect with the 303 status code, which is usually more appropriate."
    return RedirectResponse(href, status_code=HTTP.SEE_OTHER)


def chaos_icon():
    return A(
        Img(src="/Greek_lc_chi_icon64.png", height=24, width=24, cls="white"),
        title="chaos",
        role="button",
        cls="secondary outline",
        href="/",
    )


def search_form():
    return Form(
        Input(
            name="term",
            type="search",
            placeholder="Search...",
            aria_label="Search",
            autofocus=True,
        ),
        style="margin-bottom: 2px; padding-top: 0;",
        role="search",
        action="/search",
    )


def get_entry_clipboard(entry):
    return Img(
        src="/clipboard.svg",
        title="Copy entry link to clipboard",
        style="cursor: pointer; background-color: white; margin: 2px 8px;",
        cls="to_clipboard white",
        data_clipboard_action="copy",
        data_clipboard_text=f"[{entry.title}]({entry.url})",
    )


def get_entries_table(entries):
    rows = []
    for entry in entries:
        items = [get_entry_clipboard(entry), A(entry.title, href=entry.url)]
        match entry.type:
            case constants.NOTE:
                pass
            case constants.LINK:
                items.append(
                    A(get_icon("box-arrow-up-right.svg", "go to"), href=entry.href)
                )
            case constants.FILE:
                items.append(
                    A(get_icon("download.svg", title="download"), href=entry.download)
                )
        rows.append(
            Tr(
                Td(*items),
                Td(entry.size, style="text-align: right;"),
                Td(entry.modified_local),
            )
        )
    return Table(Tbody(*rows), cls="striped")


def get_icon(filename, title=""):
    return Img(
        src=f"/{filename}",
        title=title,
        style="background-color: white; margin: 2px 8px;",
    )
