"Components for output generation."

from http import HTTPStatus as HTTP

import babel.numbers
from fasthtml.common import *

import constants
import settings
import entries


class EntryConvertor(Convertor):
    "Convert path segment to Entry class instance."

    regex = "[^./]+"

    def convert(self, value: str) -> entries.Entry:
        return entries.get(value)

    def to_string(self, value: entries.Entry) -> str:
        return str(value)


register_url_convertor("Entry", EntryConvertor())


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
    elif apikey := request.headers.get("apikey"):
        if apikey == os.environ.get("CHAOS_APIKEY"):
            request.scope["auth"] = session["auth"] = os.environ["CHAOS_USERNAME"]
        else:
            return Response(content="invalid API key", status_code=HTTP.UNAUTHORIZED)
    elif request.url.path != "/":
        add_toast(session, "Login required.", "error")
        session["path"] = request.url.path
        return redirect("/")


beforeware = Beforeware(
    set_auth_before,
    skip=[r"/favicon\.ico", r"/chaos\.png", r"/mods\.css", r"/ping"],
)


def get_app_rt(routes=None):
    app, rt = fast_app(
        live=constants.DEVELOPMENT,
        static_path="static",
        before=beforeware,
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


def get_chaos_icon():
    return A(
        Img(
            src="/chaos.png",
            height=24,
            width=24,
            cls="white",
        ),
        title="chaos: Web service for a repository of notes, links and files with no intrinsic order.",
        role="button",
        cls="secondary outline no_margin",
        href="/",
    )


def get_icon(filename, title=""):
    return Img(
        src=f"/{filename}",
        title=title,
        cls="icon",
    )


def get_mimetype_icon(mimetype, title=""):
    if mimetype in constants.IMAGE_MIMETYPES:
        return get_icon("file-earmark-image.svg", title=title)
    match mimetype:
        case constants.PDF_MIMETYPE:
            return get_icon("file-earmark-pdf.svg", title=title)
        case constants.DOCX_MIMETYPE:
            return get_icon("file-earmark-word.svg", title=title)
        case constants.EPUB_MIMETYPE:
            return get_icon("file-earmark-text.svg", title=title)
    return get_icon("file-earmark-binary.svg", title=title)


def get_nav_menu(*links):
    return Details(
        Summary(Img(src="/Hamburger_icon.svg", width=24)),
        Ul(
            *[Li(l) for l in links],
            Li(A("Add note...", href="/note/")),
            Li(A("Add link...", href="/link/")),
            Li(A("Add file...", href="/file/")),
            Li(A("Keywords", href="/keywords")),
        ),
        title="Menu",
        cls="dropdown",
    )


def get_after_buttons():
    return Div(
        Div(A("Notes", href="/notes", role="button", cls="thin")),
        Div(A("Links", href="/links", role="button", cls="thin")),
        Div(A("Files", href="/files", role="button", cls="thin")),
        Div(A("No keywords", href="/nokeywords", role="button", cls="thin")),
        Div(A("Unrelated", href="/unrelated", role="button", cls="thin")),
        Div(A("Random", href="/random", role="button", cls="thin")),
        Div(A("System", href="/system", role="button", cls="outline thin")),
        Div(A("Logout", href="/logout", role="button", cls="secondary thin")),
        cls="grid",
    )


def search_form(term=None):
    return Form(
        Input(
            name="term",
            type="search",
            placeholder="Search term...",
            aria_label="Search",
            value=term or "",
            autofocus=True,
        ),
        cls="search",
        role="search",
        action="/search",
        method="GET",
    )


def get_entry_clipboard(entry):
    return Img(
        src="/clipboard.svg",
        title="Link to clipboard",
        cls="to_clipboard white",
        data_clipboard_action="copy",
        data_clipboard_text=f"[{entry.title}]({entry.url})",
    )


def get_entries_table_page(session, title, entries, page, href, after=""):
    "Get the page displaying a table of the given entries."
    total_entries = len(entries)
    page = min(max(1, page), get_total_pages(total_entries))
    start = (page - 1) * constants.MAX_PAGE_ENTRIES
    end = page * constants.MAX_PAGE_ENTRIES
    table = get_entries_table(entries[start:end])
    pager = get_table_pager(page, total_entries, href)
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(get_chaos_icon()),
                    Li(title),
                    Li(get_nav_menu()),
                    Li(search_form()),
                ),
                cls="main",
            ),
            cls="container",
        ),
        Main(table, pager, after, cls="container"),
        Footer(
            Hr(),
            Small(
                Div(
                    Div(session["auth"]),
                    Div(
                        A("chaos", href="https://github.com/pekrau/chaos"),
                        " ",
                        constants.__version__,
                        cls="right",
                    ),
                    cls="grid",
                ),
            ),
            cls="container",
        ),
    )


def get_entries_table(entries, full=True):
    rows = []
    for entry in entries[0 : constants.MAX_PAGE_ENTRIES]:
        keywords = sorted(entry.keywords)
        keywords = [str(A(kw, href=f"/keywords/{kw}")) for kw in keywords]
        if len(keywords) > constants.MAX_ROW_ITEMS:
            keywords = NotStr("; ".join(keywords[0 : constants.MAX_ROW_ITEMS]) + "...")
        else:
            keywords = NotStr("; ".join(keywords))
        match entry.__class__.__name__:
            case "Note":
                if full:
                    cells = [
                        Td(entry.size, cls="right"),
                        Td(entry.owner),
                        Td(entry.modified_local),
                    ]
                else:
                    cells = []
                rows.append(
                    Tr(
                        Td(A(entry.title, href=entry.url)),
                        Td(keywords),
                        *cells,
                    )
                )
            case "Link":
                if full:
                    cells = [
                        Td(entry.size, cls="right"),
                        Td(entry.owner),
                        Td(entry.modified_local),
                    ]
                else:
                    cells = []
                rows.append(
                    Tr(
                        Td(
                            A(
                                get_icon("box-arrow-up-right.svg", title="Go to page"),
                                href=entry.href,
                            ),
                            A(entry.title, href=entry.url),
                        ),
                        Td(keywords),
                        *cells,
                    )
                )
            case "File":
                if full:
                    cells = [
                        Td(
                            f"{entry.size} + {entry.file_size}",
                            cls="right",
                        ),
                        Td(entry.owner),
                        Td(entry.modified_local),
                    ]
                else:
                    cells = []
                rows.append(
                    Tr(
                        Td(
                            A(
                                get_mimetype_icon(
                                    entry.file_mimetype, title="View or download file"
                                ),
                                href=f"{entry.url}/data",
                            ),
                            A(entry.title, href=entry.url),
                        ),
                        Td(keywords),
                        *cells,
                    )
                )
            case _:
                raise NotImplementedError
    if rows:
        if len(entries) > constants.MAX_PAGE_ENTRIES:
            rows.append(Tr(Td(I("Others not shown..."), colspan=3)))
        return Table(Tbody(*rows), cls="striped compressed")
    else:
        return Article(I("No entries."))


def get_table_pager(current_page, total_entries, href):
    "Return form with pager buttons given current page."
    if total_entries <= constants.MAX_PAGE_ENTRIES:
        return ""
    pages = [1]
    total_pages = get_total_pages(total_entries)
    for page in range(2, total_pages):
        if abs(current_page - page) < 2:
            pages.append(page)
    if pages[-1] != total_pages:
        pages.append(total_pages)
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
    return Form(Div(*[Div(b) for b in buttons], cls="grid"), action=href)


def get_total_pages(total_entries=None):
    "Return the total number of table pages for the given number of entries."
    if total_entries is None:
        total_entries = total()
    return (total_entries - 1) // constants.MAX_PAGE_ENTRIES + 1


def get_keywords_links(entry):
    return NotStr(
        "; ".join([str(A(kw, href=f"/keywords/{kw}")) for kw in entry.keywords])
    )


def numerical(n):
    "Return numerical value as string formatted according to locale."
    return babel.numbers.format_decimal(n, locale=constants.DEFAULT_LOCALE)
