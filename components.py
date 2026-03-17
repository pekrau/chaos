"Components for output generation."

from http import HTTPStatus as HTTP
import os
from urllib.parse import urlsplit

from fasthtml.common import *
import marko

import constants
import errors
import items
import markdown
import utils


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
    """Replacement of the default static response handler.
    Required since the 'static' convertor has been made useless, which
    in turn was needed to enable using file extensions for determining
    format of the data content for different items. The predefined
    'static' convertor somehow prevented this.
    """

    regex = "static_do_not_match_anything_at_all"


register_url_convertor("static", StaticNoMatchConvertor())


def get_app_rt(routes=None):
    app, rt = fast_app(
        before=Beforeware(
            check_auth_before,
            skip=["/login", r"/static/.*"],
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


def check_auth_before(request, session):
    if session.get("auth", None):
        return
    if password := request.headers.get("password"):
        if password == os.environ.get("CHAOS_PASSWORD"):
            session["auth"] = "logged in"
            return
        else:
            return Response(content="Invalid password", status_code=HTTP.UNAUTHORIZED)
    add_toast(session, "Login required.", "error")
    session["path"] = request.url.path
    return redirect("/login")


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
    return get_type_icon(item.__class__.__name__)


def get_type_icon(type):
    match type:
        case "Note":
            return get_note_icon()
        case "Link":
            return get_link_icon()
        case "File":
            return get_file_icon()
        case "Image":
            return get_image_icon()
        case "Database":
            return get_database_icon()
        case "Graphic":
            return get_graphic_icon()
        case "Book":
            return get_book_icon()
        case "Article":
            return get_article_icon()
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


def get_book_icon(title="Book"):
    return get_icon("book.svg", title=title)


def get_article_icon(title="Article"):
    return get_icon("journal-text.svg", title=title)


def get_nav_menu(item=None, copy=True):
    links = [A("Home", href="/")]
    if item:
        links.append(A(f"Edit {item.type}", href=f"{item.url}/edit"))
        if copy:
            links.append(A(f"Copy {item.type}", href=f"{item.url}/copy"))
        if item.pinned:
            links.append(A(f"Unpin {item.type}", href=f"/unpin/{item.id}"))
        else:
            links.append(A(f"Pin {item.type}", href=f"/pin/{item.id}"))
        links.append(A(f"Delete {item.type}", href=f"{item.url}/delete"))
    links.append(A("Search...", href="/search"))
    links.append(A("Add...", href="/add/"))
    links.append(A("System", href="/system"))
    links.append(A("Logout", href="/logout"))
    return Details(
        Summary(get_chaos_icon()),
        Ul(*[Li(l) for l in links]),
        title="chaos: Web-based repository of items with no intrinsic order.",
        cls="dropdown",
    )


def get_shortcuts_menu(item=None):
    entries = [Li(Strong(get_item_link(i, full=False))) for i in items.get_pinned()]
    entries.extend([Li(get_item_link(i, full=False)) for i in items.get_recent(item)])
    result = Details(
        Summary("Shortcuts..."),
        Ul(*entries),
        cls="dropdown",
    )
    if item:
        items.write_state(recent=item)
    return result


def to_clipboard(item):
    return get_icon(
        "markdown.svg",
        title="Copy Markdown for xref to clipboard",
        cls="icon to_clipboard",
        data_clipboard_text=f"[[{item.id}]]",
    )


def clipboard_script():
    return Script(src="/static/clipboard.min.js")


def clipboard_activate():
    return Script("new ClipboardJS('.to_clipboard');", type="text/javascript")


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
        Card(Header("Referred from"), get_items_list(xrefs_from)),
        Card(Header("Refers to"), get_items_list(xrefs_to)),
        cls="grid",
    )


def get_items_list(items):
    if rows := get_items_list_rows(items):
        return Table(Tbody(*rows), cls="compressed")
    else:
        return I("No items.")


def get_items_list_rows(items):
    rows = []
    for item in items:
        rows.append(
            Tr(
                Td(get_item_link(item)),
                Td(item.n_xrefs or ""),
                Td(item.age, cls="nobr"),
                Td(to_clipboard(item)),
            )
        )
    return rows


def get_item_link(item, full=True):
    "Get link to item. For link type, also provide link to external href."
    match item.type:
        case "note":
            return A(get_note_icon(), item.title, href=item.url)
        case "link":
            if full:
                return Span(
                    A(get_link_icon(), item.title, href=item.url),
                    ", ",
                    A(
                        urlsplit(item.href).hostname,
                        href=item.href,
                        target="_blank",
                        cls="contrast",
                    ),
                )
            else:
                return A(get_link_icon(), item.title, href=item.url)
        case "image":
            return A(get_image_icon(), item.title, href=item.url)
        case "file":
            if full:
                return Span(
                    A(get_file_icon(item.file_mimetype), item.title, href=item.url),
                    ", ",
                    A(f"[{item.ext}]", href=item.url_file, cls="contrast"),
                )
            else:
                return A(get_file_icon(item.file_mimetype), item.title, href=item.url)
        case "database":
            return A(get_database_icon(), item.title, href=item.url)
        case "graphic":
            return A(get_graphic_icon(), item.title, href=item.url)
        case "book":
            return A(get_book_icon(), item.title, href=item.url)
        case "article":
            return A(get_article_icon(), item.title, href=item.url)
        case _:
            raise NotImplementedError


def get_items_display_pager(current_page, total_items):
    "Return pager buttons given current page."
    if total_items <= constants.MAX_PAGE_ITEMS:
        return ""
    pages = [1]
    total_pages = utils.get_total_pages(total_items)
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
    return Div(*[Div(b) for b in buttons], cls="grid")


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
