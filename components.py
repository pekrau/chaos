"Components for output generation."

from http import HTTPStatus as HTTP
import os

from fasthtml.common import *
import marko

import constants
import errors
import items
import markdown


class ItemConvertor(Convertor):
    "Convert path segment to Item class instance."

    regex = "[^./]+"

    def convert(self, value: str) -> items.Item:
        return items.get(value)

    def to_string(self, value: items.Item) -> str:
        return str(value)


register_url_convertor("Item", ItemConvertor())


class NameConvertor(StringConvertor):

    regex = "[^./]+"


register_url_convertor("Name", NameConvertor())


class ExtConvertor(StringConvertor):

    regex = "\\.[^./]+"


register_url_convertor("Ext", ExtConvertor())


class StaticNoMatchConvertor(StringConvertor):
    """To bypass the standard 'static' convertor.
    Required since the 'static' convertor has been made useless, which
    in turn was needed to enable using file extensions for determining
    format of the data content for '/data' resources. The
    predefined 'static' convertor somehow prevented this.
    """

    regex = "static_do_not_match_anything_at_all"


register_url_convertor("static", StaticNoMatchConvertor())


def get_app_rt(routes=None):
    app, rt = fast_app(
        before=Beforeware(
            set_auth_before,
            skip=[r"/static/.*"],
        ),
        hdrs=(
            Link(rel="stylesheet", href="/static/modifications.css", type="text/css"),
            Link(rel="icon", href="/static/favicon.ico", type="image/x-icon"),
        ),
        exception_handlers={errors.Error: errors.error_handler},
        routes=routes,
    )
    setup_toasts(app)
    return app, rt


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


def redirect(href):
    "Redirect with the 303 status code, which is usually more appropriate."
    return RedirectResponse(href, status_code=HTTP.SEE_OTHER)


def get_icon(filename, title="", **kwargs):
    defaults = dict(cls="icon")
    defaults.update(kwargs)
    return Img(
        src=f"/static/{filename}", title=title, width="24", height="24", **defaults
    )


def get_chaos_icon():
    return Img(
        src="/static/chaos.png",
        width=24,
        height=24,
        cls="white",
    )


def get_question_icon():
    return get_icon("question-circle.svg")


def get_item_icon(item):
    match item.__class__.__name__:
        case "Note":
            return get_note_icon()
        case "Link":
            return get_link_icon()
        case "File":
            return get_file_icon(item.file_mimetype)
        case "Image":
            return get_image_icon()
        case "Graphic":
            return get_graphic_icon()
        case "Database":
            return get_database_icon()
        case _:
            raise NotImplementedError


def get_note_icon(title="Note"):
    return get_icon("card-text.svg", title=title)


def get_link_icon(title="Link"):
    return get_icon("box-arrow-up-right.svg", title=title)


def get_file_icon(mimetype=None, title="", **kwargs):
    match mimetype:
        case constants.PDF_MIMETYPE:
            return get_icon("file-earmark-pdf.svg", title=title, **kwargs)
        case constants.DOCX_MIMETYPE:
            return get_icon("file-earmark-word.svg", title=title, **kwargs)
        case constants.EPUB_MIMETYPE:
            return get_icon("file-earmark-text.svg", title=title, **kwargs)
        case constants.CSV_MIMETYPE:
            return get_icon("filetype-csv.svg", title=title, **kwargs)
        case constants.JSON_MIMETYPE:
            return get_icon("filetype-json.svg", title=title, **kwargs)
    return get_icon("file-earmark-binary.svg", title=title, **kwargs)


def get_image_icon(title="Image"):
    return get_icon("file-earmark-image.svg", title=title)


def get_database_icon(title="Database"):
    return get_icon("database.svg", title=title)


def get_graphic_icon(title="Graphic"):
    return get_icon("graph-up.svg", title=title)


def get_nav_menu(item=None):
    links = [A("Home", href="/"), A("Search...", href="/search")]
    if item:
        links.append(A(f"Edit {item.type}", href=f"{item.url}/edit"))
        links.append(A(f"Copy {item.type}", href=f"{item.url}/copy"))
        links.append(A(f"Delete {item.type}", href=f"{item.url}/delete"))
        links.append(
            Span(
                "Xref to clipboard",
                cls="to_clipboard",
                data_clipboard_text=f"[[{item.id}]]",
            )
        )
    links.append(A("Add...", href="/add/"))
    links.append(A("Notes", href="/notes")),
    links.append(A("Links", href="/links"))
    links.append(A("Images", href="/images"))
    links.append(A("Files", href="/files"))
    links.append(A("Databases", href="/databases"))
    links.append(A("Graphics", href="/graphics"))
    links.append(A("Random", href="/random"))
    links.append(A("System", href="/system"))
    links.append(A("Logout", href="/logout"))
    return Details(
        Summary(get_chaos_icon()),
        Ul(*[Li(l) for l in links]),
        title="chaos: Web-based repository of items with no intrinsic order.",
        cls="dropdown",
    )


def get_item_clipboard(item):
    return get_icon(
        "markdown.svg",
        title="Copy Markdown xref to clipboard",
        cls="icon to_clipboard",
        data_clipboard_text=f"[[{item.id}]]",
    )


def clipboard_script():
    return Script(src="/static/clipboard.min.js")


def clipboard_activate():
    return Script("new ClipboardJS('.to_clipboard');", type="text/javascript")


def get_items_table_page(title, items, page, href, type=""):
    "Get the page displaying a table of the given items."
    total_items = len(items)
    page = min(max(1, page), get_total_pages(total_items))
    start = (page - 1) * constants.MAX_PAGE_ITEMS
    end = page * constants.MAX_PAGE_ITEMS
    table = get_items_table(items[start:end])
    pager = get_table_pager(page, total_items, href)
    return (
        Title(title),
        clipboard_script(),
        Header(
            Nav(
                Ul(
                    Li(get_nav_menu()),
                    Li(title),
                ),
                Ul(
                    Li(get_search_form(type=type)),
                ),
            ),
            cls="container",
        ),
        Main(table, pager, cls="container"),
        clipboard_activate(),
    )


def get_search_form(type=""):
    return Form(
        Input(type="hidden", name="type", value=type),
        Input(
            type="search",
            name="term",
            placeholder="Search...",
            aria_label="Search",
        ),
        cls="search",
        role="search",
        action="/search",
        method="GET",
    )


def get_text_card(item):
    if text := item.text:
        return Card(NotStr(markdown.to_html(text)))
    else:
        return Card(I("No text."))


def get_xrefs_card(item):
    "Show the xrefs that other items make to this item."
    xrefs_from = sorted(
        [items.get(id) for id in item.xrefs_to_self],
        key=lambda i: i.modified,
        reverse=True,
    )
    xrefs_to = sorted(
        [items.get(id) for id in item.xrefs_from_self],
        key=lambda i: i.modified,
        reverse=True,
    )
    return Div(
        Card(Header("Referred from"), get_items_table(xrefs_from, max_items=None)),
        Card(Header("Refers to"), get_items_table(xrefs_to, max_items=None)),
        cls="grid",
    )


def get_items_table(items, max_items=constants.MAX_PAGE_ITEMS, edit=False):
    rows = []
    if max_items:
        items = items[0:max_items]
    for item in items:
        match item.__class__.__name__:
            case "Note":
                icon = A(get_note_icon(), href=item.url)
            case "Link":
                icon = A(
                    get_link_icon(title="Follow link..."),
                    href=item.href,
                    target="_blank",
                )
            case "Database":
                icon = A(get_database_icon(), href=item.url)
            case "Graphic":
                icon = A(get_graphic_icon(), href=item.url)
            case "Image":
                icon = A(get_image_icon(title="View image"), href=item.url_file)
            case "File":
                icon = A(
                    get_file_icon(item.file_mimetype, title="View or download file"),
                    href=item.url_file,
                )
            case _:
                raise NotImplementedError
        if edit:
            rows.append(
                Tr(
                    Td(icon, A(item.title, href=item.url)),
                    Td(
                        Select(
                            name=f"position_{item.id}",
                            *[
                                Option(str(i), selected=i == len(rows) + 1)
                                for i in range(0, len(items) + 2)
                            ],
                            cls="slim",
                        ),
                    ),
                    Td(
                        Input(type="checkbox", name="remove", value=item.id),
                        "Remove",
                        cls="right",
                    ),
                )
            )
        else:
            rows.append(
                Tr(
                    Td(icon, A(item.title, href=item.url)),
                    Td(get_item_clipboard(item), cls="right"),
                )
            )
    if rows:
        if len(items) > constants.MAX_PAGE_ITEMS:
            rows.append(Tr(Td(I("Some not shown..."), colspan=3)))
        return Table(Tbody(*rows), cls="compressed")
    else:
        return I("No items.")


def get_table_pager(current_page, total_items, href):
    "Return form with pager buttons given current page."
    if total_items <= constants.MAX_PAGE_ITEMS:
        return ""
    pages = [1]
    total_pages = get_total_pages(total_items)
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


def get_title_input(title=""):
    return Input(
        type="text",
        name="title",
        value=title,
        placeholder="Title...",
        required=True,
    )


def get_text_input(text=""):
    return (
        Textarea(
            text,
            name="text",
            rows=10,
            placeholder="Text...",
        ),
    )


def get_cancel_form(href):
    return Form(
        Input(
            type="submit",
            value="Cancel",
            cls="secondary",
        ),
        action=href,
        method="GET",
    )


def get_total_pages(total_items=None):
    "Return the total number of table pages for the given number of items."
    if total_items is None:
        total_items = total()
    return (total_items - 1) // constants.MAX_PAGE_ITEMS + 1
