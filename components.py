"Components for output generation."

from http import HTTPStatus as HTTP
import os

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
            Link(rel="stylesheet", href="/static/style_modifications.css", type="text/css"),
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
    return Img(src=f"/static/{filename}", title=title, width="24", height="24", **defaults)


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
        # case constants.CSV_MIMETYPE:
        #     return get_icon("filetype-csv.svg", title=title, **kwargs)
        # case constants.JSON_MIMETYPE:
        #     return get_icon("filetype-json.svg", title=title, **kwargs)
    return get_icon("file-earmark-binary.svg", title=title, **kwargs)


def get_image_icon(title="Image"):
    return get_icon("file-earmark-image.svg", title=title)


def get_database_icon(title="Database"):
    return get_icon("database.svg", title=title)


def get_graphic_icon(title="Graphic"):
    return get_icon("graph-up.svg", title=title)


def get_listset_icon(title="Listset"):
    return get_icon("list-ul.svg", title=title)


def get_nav_menu():
    return Details(
        Summary(
            Img(
                src="/static/chaos.png",
                width=24,
                height=24,
                cls="white",
            ),
        ),
        Ul(
            Li(A("Home", href="/")),
            Li(A("Add...", href="/add/")),
            Li(A("Notes", href="/notes")),
            Li(A("Links", href="/links")),
            Li(A("Images", href="/images")),
            Li(A("Files", href="/files")),
            Li(A("Databases", href="/databases")),
            Li(A("Graphics", href="/graphics")),
            Li(A("Listsets", href="/listsets")),
            Li(A("Keywords", href="/keywords")),
            Li(A("Without keywords", href="/withoutkeywords")),
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
        ),
        cls="search",
        role="search",
        action="/search",
        method="GET",
    )


def get_item_links(item):
    return [
        A(
            get_icon("pencil.svg", title=f"Edit {item.name}"),
            href=f"{item.url}/edit",
        ),
        A(
            get_icon("copy.svg", title=f"Copy {item.name}"),
            href=f"{item.url}/copy",
        ),
        A(
            get_icon("trash.svg", title=f"Delete {item.name}"),
            href=f"{item.url}/delete",
        ),
    ] + get_item_clipboards(item)


def get_item_clipboards(item):
    return [
        get_icon(
            "info-square.svg",
            title="Copy identifier to clipboard",
            cls="icon to_clipboard",
            data_clipboard_text=item.id,
        ),
        get_icon(
            "markdown.svg",
            title="Copy Markdown link to clipboard",
            cls="icon to_clipboard",
            data_clipboard_text=f"[{item.title}]({item.url})",
        ),
    ]


def clipboard_script():
    return Script(src="/static/clipboard.min.js")


def clipboard_activate():
    return Script("new ClipboardJS('.to_clipboard');", type="text/javascript")


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
        clipboard_script(),
        Header(
            Nav(
                Ul(
                    Li(get_nav_menu()),
                    Li(title),
                ),
                Ul(Li(search_form())),
            ),
            cls="container",
        ),
        Main(table, pager, after, cls="container"),
        clipboard_activate(),
    )


def get_text_card(item):
    if text := item.text:
        return Card(NotStr(marko.convert(text)))
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
            Header(
                Span("Keywords"),
                A(
                    "Similar items",
                    href=f"/similar/{item.id}",
                    role="button",
                    cls="thin",
                ),
                cls="grid",
            ),
            keywords_links,
        )
    else:
        return Card("No keywords.")


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
            case "Graphic":
                icon = A(get_graphic_icon(), href=item.url)
            case "Image":
                icon = A(get_image_icon(title="View image"), href=item.url_file)
            case "File":
                icon = A(
                    get_file_icon(item.file_mimetype, title="View or download file"),
                    href=item.url_file,
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
                    Td(*get_item_clipboards(item), cls="right"),
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


def get_title_input(item):
    return Input(
        type="text",
        name="title",
        value=item.title if item else "",
        placeholder="Title...",
        required=True,
        autofocus=item is None,
    )


def get_text_input(item):
    return (
        Textarea(
            item.text if item else "",
            name="text",
            rows=10,
            placeholder="Text...",
        ),
    )


def get_listset_keyword_inputs(item):
    return Div(
        get_listset_input(item),
        get_keyword_input(item),
        cls="grid",
    )


def get_listset_input(item, max_listsets=constants.MAX_LISTSETS):
    listsets = items.get_possible_listsets(item)
    listsets.sort(key=lambda i: i.modified, reverse=True)
    listsets = listsets[:max_listsets]
    return Details(
        Summary("Add to listsets..."),
        Ul(
            *[
                Li(
                    Label(
                        Input(type="checkbox", name="listsets", value=listset.id),
                        listset.title,
                    )
                )
                for listset in listsets
            ]
        ),
        cls="dropdown",
    )


def get_keyword_input(item):
    return Details(
        Summary("Keywords..."),
        Ul(*get_keywords_dropdown(item.keywords if item else list())),
        cls="dropdown",
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
