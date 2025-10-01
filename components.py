"Components for output generation."

from http import HTTPStatus as HTTP

from fasthtml.common import *

import constants
import settings


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
        live=constants.DEVELOPMENT,
        static_path="static",
        before=Beforeware(set_auth_before),
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


def get_add_dropdown():
    return Details(
        Summary("Add..."),
        Ul(
            Li(A("Note", href="/note")),
            Li(A("Link", href="/link")),
            Li(A("File", href="/file")),
        ),
        cls="dropdown",
    )


def search_form(term=None):
    return Form(
        Input(
            name="term",
            type="search",
            placeholder="Search...",
            aria_label="Search",
            value=term or "",
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
        keywords = settings.get_original_keywords(sorted(entry.keywords))
        keywords = [str(A(kw, href=f"/keywords/{kw}")) for kw in keywords]
        if len(keywords) > constants.MAX_ROW_ITEMS:
            keywords = NotStr("; ".join(keywords[0 : constants.MAX_ROW_ITEMS]) + "...")
        else:
            keywords = NotStr("; ".join(keywords))
        items = [get_entry_clipboard(entry), A(entry.title, href=entry.url)]
        match entry.__class__.__name__:
            case "Note":
                rows.append(
                    Tr(
                        Td(*items),
                        Td(keywords),
                        Td(entry.size, style="text-align: right;"),
                        Td(entry.owner),
                        Td(entry.modified_local),
                    )
                )
            case "Link":
                items.append(
                    A(
                        get_icon("box-arrow-up-right.svg", title="Go to page"),
                        href=entry.href,
                    )
                )
                rows.append(
                    Tr(
                        Td(*items),
                        Td(keywords),
                        Td(entry.size, style="text-align: right;"),
                        Td(entry.owner),
                        Td(entry.modified_local),
                    )
                )
            case "File":
                items.append(
                    A(
                        get_icon("download.svg", title="Download file"),
                        href=f"{entry.url}/download",
                    )
                )
                rows.append(
                    Tr(
                        Td(*items),
                        Td(keywords),
                        Td(
                            f"{entry.size} + {entry.filesize}",
                            style="text-align: right;",
                        ),
                        Td(entry.owner),
                        Td(entry.modified_local),
                    )
                )
            case _:
                raise NotImplementedError
    return Table(Tbody(*rows), cls="striped")


def get_icon(filename, title=""):
    return Img(
        src=f"/{filename}",
        title=title,
        style="background-color: white; margin: 2px 8px;",
    )


def get_table_pager(current_page, total_entries, action):
    "Return form with pager buttons given current page."
    if total_entries < constants.MAX_PAGE_ENTRIES:
        return ""
    pages = [1]
    max_pages = (total_entries + 1) // constants.MAX_PAGE_ENTRIES
    for page in range(2, max_pages):
        if abs(current_page - page) < 2:
            pages.append(page)
    if pages[-1] != max_pages:
        pages.append(max_pages)
    buttons = []
    prev_page = 1
    for page in pages:
        if prev_page + 1 < page:
            buttons.append(
                Input(
                    type="submit",
                    value="...",
                    disabled=True,
                    cls="outline secondary",
                )
            )
        if page == current_page:
            buttons.append(
                Input(
                    type="submit",
                    name="page",
                    value=str(page),
                    disabled=True,
                    cls="secondary",
                )
            )
        else:
            buttons.append(Input(type="submit", name="page", value=str(page)))
        prev_page = page
    return Form(Div(*[Div(b) for b in buttons], cls="grid"), action=action)
