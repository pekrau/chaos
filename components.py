"Components for output generation."

from http import HTTPStatus as HTTP
import os

import babel.numbers
from fasthtml.common import *
import marko

import constants
import errors
import settings
import items


class ItemConvertor(Convertor):
    "Convert path segment to Item class instance."

    regex = "[^./]+"

    def convert(self, value: str) -> items.Item:
        return items.get(value)

    def to_string(self, value: items.Item) -> str:
        return str(value)


register_url_convertor("Item", ItemConvertor())


class CsvConvertor(StringConvertor):
    "Accept name with CSV extension."

    # regex = "[^./]+\\.csv"
    regex = r"[^/.]+\.csv"


register_url_convertor("Csv", CsvConvertor())


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


def get_app_rt(routes=None):
    app, rt = fast_app(
        static_path="static",
        before=Beforeware(
            set_auth_before,
            skip=[r"/favicon\.ico", r"/chaos\.png", r"/mods\.css", r"/ping"],
        ),
        hdrs=(Link(rel="stylesheet", href="/mods.css", type="text/css"),),
        exception_handlers={
            errors.Error: errors.error_handler,
        },
        routes=routes,
    )
    setup_toasts(app)
    return app, rt


def redirect(href):
    "Redirect with the 303 status code, which is usually more appropriate."
    return RedirectResponse(href, status_code=HTTP.SEE_OTHER)


def get_icon(filename, title="", **kwargs):
    defaults = dict(cls="icon")
    defaults.update(kwargs)
    return Img(src=f"/{filename}", title=title, width="24", height="24", **defaults)


def get_note_icon(title="Note"):
    return get_icon("card-text.svg", title=title)


def get_link_icon(title="Link"):
    return get_icon("box-arrow-up-right.svg", title=title)


def get_image_icon(title="Image"):
    return get_icon("file-earmark-image.svg", title=title)


def get_listset_icon(title="Listset"):
    return get_icon("list-ul.svg", title=title)


def get_database_icon(title="Database"):
    return get_icon("database.svg", title=title)


def get_file_icon(mimetype=None, title=""):
    match mimetype:
        case constants.PDF_MIMETYPE:
            return get_icon("file-earmark-pdf.svg", title=title)
        case constants.DOCX_MIMETYPE:
            return get_icon("file-earmark-word.svg", title=title)
        case constants.EPUB_MIMETYPE:
            return get_icon("file-earmark-text.svg", title=title)
    return get_icon("file-earmark-binary.svg", title=title)


def get_nav_menu():
    return Details(
        Summary(
            Img(
                src="/chaos.png",
                width=24,
                height=24,
                cls="white",
            ),
        ),
        Ul(
            Li(A("Home", href="/")),
            Li(A("Add note...", href="/note/")),
            Li(A("Add link...", href="/link/")),
            Li(A("Add image...", href="/image/")),
            Li(A("Add file...", href="/file/")),
            Li(A("Add database...", href="/database/")),
            Li(A("Add listset...", href="/listset/")),
            Li(A("Keywords", href="/keywords")),
            Li(A("Notes", href="/notes")),
            Li(A("Links", href="/links")),
            Li(A("Images", href="/images")),
            Li(A("Files", href="/files")),
            Li(A("Databases", href="/databases")),
            Li(A("Listsets", href="/listsets")),
            Li(A("No keywords", href="/nokeywords")),
            Li(A("No similar", href="/nosimilar")),
            Li(A("Random", href="/random")),
            Li(A("System", href="/system")),
            Li(A("Logout", href="/logout")),
        ),
        title="chaos: Web-based repository of notes, links, images and files with no intrinsic order.",
        cls="dropdown",
    )


def search_form(term=None):
    return Form(
        Input(
            type="search",
            name="term",
            placeholder="Search...",
            aria_label="Search",
            value=term or "",
            autofocus=True,
        ),
        cls="search",
        role="search",
        action="/search",
        method="GET",
    )


def get_item_edit_link(item):
    return A(
        get_icon("pencil.svg", title=f"Edit {item.name}"),
        href=f"{item.url}/edit",
    )


def get_item_copy_link(item):
    return A(
        get_icon("copy.svg", title=f"Edit {item.name}"),
        href=f"{item.url}/copy",
    )


def get_item_id_to_clipboard(item):
    return get_icon(
        "info-square.svg", title="Copy identifier to clipboard", cls="icon to_clipboard"
    )


def get_item_md_link_to_clipboard(item):
    return get_icon(
        "markdown.svg", title="Copy Markdown link to clipboard", cls="icon to_clipboard"
    )


def get_item_delete_link(item):
    return A(
        get_icon("trash.svg", title=f"Delete {item.name}"),
        href=f"{item.url}/delete",
    )


def get_item_links(item):
    return [
        get_item_edit_link(item),
        " ",
        get_item_copy_link(item),
        " ",
        get_item_id_to_clipboard(item),
        " ",
        get_item_md_link_to_clipboard(item),
        " ",
        get_item_delete_link(item),
    ]


def get_items_table_page(title, items, page, href, after=""):
    "Get the page displaying a table of the given items."
    total_items = len(items)
    page = min(max(1, page), get_total_pages(total_items))
    start = (page - 1) * constants.MAX_PAGE_ITEMS
    end = page * constants.MAX_PAGE_ITEMS
    table = get_items_table(items[start:end])
    pager = get_table_pager(page, total_items, href)
    return (
        Title(title),
        Script(src="/clipboard.min.js"),
        Script("new ClipboardJS('.to_clipboard');"),
        Header(
            Nav(
                Ul(
                    Li(get_nav_menu()),
                    Li(title),
                    Li(search_form()),
                ),
                cls="main",
            ),
            cls="container",
        ),
        Main(table, pager, after, cls="container"),
    )


def get_text_card(item):
    if item.text:
        return Card(NotStr(marko.convert(item.text)))
    else:
        return Card(I("No text."))


def get_listsets_card(item):
    if listsets := list(item.listsets):
        return Card(
            Header("In listsets"),
            get_items_table(listsets),
        )
    else:
        return Card(I("In no listsets."))


def get_keywords_card(item):
    if keywords_links := get_keywords_links(item):
        return Card(
            Div("Keywords: ", keywords_links),
            Div(
                A("Similar items", href=f"/similar/{item.id}", role="button"),
                cls="right",
            ),
        )
    else:
        return Card(I("No keywords."))


def get_items_table(items, max_items=constants.MAX_PAGE_ITEMS, edit=False):
    rows = []
    items = items[0:max_items]
    for item in items:
        keywords = sorted(item.keywords)
        keywords = [str(A(kw, href=f"/keywords/{kw}")) for kw in keywords]
        if len(keywords) > constants.MAX_ROW_KEYWORDS:
            keywords = NotStr(
                ", ".join(keywords[0 : constants.MAX_ROW_KEYWORDS]) + "..."
            )
        else:
            keywords = NotStr(", ".join(keywords))
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
            case "Image":
                icon = A(get_image_icon(title="View image"), href=item.bin_url)
            case "File":
                icon = A(
                    get_file_icon(item.file_mimetype, title="View or download file"),
                    href=item.bin_url,
                )
            case "Listset":
                icon = A(get_listset_icon(), href=item.url)
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
                    Td(get_keywords_links(item, limit=True)),
                    Td(*get_item_links(item), cls="right"),
                )
            )
    if rows:
        if len(items) > constants.MAX_PAGE_ITEMS:
            rows.append(Tr(Td(I("Some not shown..."), colspan=3)))
        return Table(Tbody(*rows), cls="striped compressed")
    else:
        return Article(I("No items."))


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


def get_keywords_dropdown(keywords):
    "Return a dropdown menu for keywords, with provides ones checked."
    return [
        Li(
            Label(
                Input(
                    type="checkbox", name="keywords", value=kw, checked=kw in keywords
                ),
                kw,
            )
        )
        for kw in settings.get_all_keywords()
    ]


def get_listsets_dropdown(item, max_listsets=constants.MAX_LISTSETS):
    "Return a dropdown of candidate listsets for the item."
    listsets = []
    for listset in items.get_items(items.Listset):
        if item in listset:
            continue
        if item is listset:
            continue
        if isinstance(item, items.Listset) and item in listset.flattened():
            continue
        listsets.append(listset)
        if max_listsets and len(listsets) >= max_listsets:
            break
    return [
        Li(
            Label(
                Input(type="checkbox", name="listsets", value=listset.id),
                listset.title,
            )
        )
        for listset in listsets
    ]


def get_keywords_links(item, limit=False):
    "Return the list of keywords for the item as links."
    result = [str(A(kw, href=f"/keywords/{kw}")) for kw in sorted(item.keywords)]
    if limit and len(result) > constants.MAX_ROW_KEYWORDS:
        return NotStr(", ".join(result[0 : constants.MAX_ROW_KEYWORDS]) + "...")
    else:
        return NotStr(", ".join(result))


def get_total_pages(total_items=None):
    "Return the total number of table pages for the given number of items."
    if total_items is None:
        total_items = total()
    return (total_items - 1) // constants.MAX_PAGE_ITEMS + 1


def numerical(n):
    "Return numerical value as string formatted according to locale."
    return babel.numbers.format_decimal(n, locale=constants.DEFAULT_LOCALE)
