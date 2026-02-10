"Link item pages."

import urllib.parse

from fasthtml.common import *

import components
import constants
import items

app, rt = components.get_app_rt()


@rt("/")
def get(request):
    "Form for adding a link."
    return (
        Title("Add link"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(components.get_link_icon(), "Add link"),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                Div(
                    Input(
                        type="text",
                        name="title",
                        placeholder="Title...",
                        required=True,
                        autofocus=True,
                    ),
                    Details(
                        Summary("Keywords..."),
                        Ul(*components.get_keywords_dropdown(keywords=list())),
                        cls="dropdown",
                    ),
                    Details(
                        Summary("Add to listsets..."),
                        Ul(*components.get_listsets_dropdown(None)),
                        cls="dropdown",
                    ),
                    cls="grid",
                ),
                Input(
                    type="href",
                    name="href",
                    placeholder="Href...",
                    required=True,
                ),
                Textarea(
                    name="text",
                    rows=10,
                    placeholder="Text...",
                ),
                Input(
                    type="submit",
                    value="Save",
                ),
                action="/link/",
                method="POST",
            ),
            Form(
                Input(
                    type="submit",
                    value="Cancel",
                    cls="secondary",
                ),
                action=request.headers["Referer"],
                method="GET",
            ),
            cls="container",
        ),
    )


@rt("/")
def post(
    session,
    title: str,
    href: str,
    text: str,
    keywords: list[str] = None,
    listsets: list[str] = None,
):
    "Actually add the link."
    link = items.Link()
    # XXX For some reason, 'auth' is not set in 'request.scope'?
    link.owner = session["auth"]
    link.title = title.strip() or "no title"
    link.href = href.strip() or "/"
    link.text = text.strip()
    link.keywords = keywords or list()
    for id in listsets or list():
        listset = items.get(id)
        assert isinstance(listset, items.Listset)
        listset.add(link)
        listset.write()
    link.write()
    return components.redirect(link.url)


@rt("/{link:Item}")
def get(link: items.Item):
    "View the metadata for the link."
    assert isinstance(link, items.Link)
    return (
        Title(link.title),
        Script(src="/clipboard.min.js"),
        Script("new ClipboardJS('.to_clipboard');"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(components.get_link_icon(), Strong(link.title)),
                    Li(*components.get_item_links(link)),
                ),
                Ul(Li(components.search_form())),
            ),
            cls="container",
        ),
        Main(
            Card(
                Strong(
                    A(
                        link.href,
                        href=link.href,
                        target="_blank",
                    )
                )
            ),
            components.get_text_card(link),
            components.get_listsets_card(link),
            components.get_keywords_card(link),
            cls="container",
        ),
        Footer(
            Hr(),
            Div(
                Div(link.modified_local),
                Div(f"{link.size} bytes"),
                Div(link.owner),
                cls="grid",
            ),
            cls="container",
        ),
    )


@rt("/{link:Item}/edit")
def get(request, link: items.Item):
    "Form for editing a link."
    assert isinstance(link, items.Link)
    return (
        Title("Edit"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Edit '{link.title}'"),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                Div(
                    Input(
                        type="text",
                        name="title",
                        value=link.title,
                        placeholder="Title...",
                        required=True,
                    ),
                    Details(
                        Summary("Keywords..."),
                        Ul(*components.get_keywords_dropdown(link.keywords)),
                        cls="dropdown",
                    ),
                    Details(
                        Summary("Add to listsets..."),
                        Ul(*components.get_listsets_dropdown(link)),
                        cls="dropdown",
                    ),
                    cls="grid",
                ),
                Input(
                    type="href",
                    name="href",
                    value=link.href,
                    placeholder="Href...",
                    required=True,
                ),
                Textarea(
                    link.text,
                    name="text",
                    rows=10,
                    placeholder="Text...",
                    autofocus=True,
                ),
                Input(
                    type="submit",
                    value="Save",
                ),
                action=f"{link.url}/edit",
                method="POST",
            ),
            Form(
                Input(
                    type="submit",
                    value="Cancel",
                    cls="secondary",
                ),
                action=request.headers["Referer"],
                method="GET",
            ),
            cls="container",
        ),
    )


@rt("/{link:Item}/edit")
def post(
    link: items.Item,
    title: str,
    href: str,
    text: str,
    keywords: list[str] = None,
    listsets: list[str] = None,
):
    "Actually edit the link."
    assert isinstance(link, items.Link)
    link.title = (title or "no title").strip()
    link.href = href.strip() or "/"
    link.text = text.strip()
    link.keywords = keywords or list()
    for id in listsets or list():
        listset = items.get(id)
        assert isinstance(listset, items.Listset)
        listset.add(link)
        listset.write()
    link.write()
    return components.redirect(link.url)


@rt("/{link:Item}/copy")
def get(request, link: items.Item):
    "Form for making a copy of the link."
    assert isinstance(link, items.Link)
    return (
        Title("Copy"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Copy '{link.title}'"),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                Input(
                    type="text",
                    name="title",
                    value=link.title,
                    placeholder="Title...",
                    required=True,
                    autofocus=True,
                ),
                Input(
                    type="submit",
                    value="Save",
                ),
                action=f"{link.url}/copy",
                method="POST",
            ),
            Form(
                Input(
                    type="submit",
                    value="Cancel",
                    cls="secondary",
                ),
                action=request.headers["Referer"],
                method="GET",
            ),
            cls="container",
        ),
    )


@rt("/{source:Item}/copy")
def post(session, source: items.File, title: str):
    "Actually copy the link."
    assert isinstance(source, items.Link)
    link = items.Link()
    # XXX For some reason, 'auth' is not set in 'request.scope'?
    link.owner = session["auth"]
    link.title = title.strip()
    link.href = source.href
    link.text = source.text
    link.keywords = source.keywords
    link.write()
    return components.redirect(link.url)


@rt("/{link:Item}/delete")
def get(request, link: items.Item):
    "Ask for confirmation to delete the link."
    assert isinstance(link, items.Link)
    redirect = urllib.parse.urlsplit(request.headers["Referer"]).path
    if redirect == f"/link/{link.id}":
        redirect = "/links"
    return (
        Title("Delete"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Delete '{link.title}'"),
                ),
            ),
            cls="container",
        ),
        Main(
            P("Really delete the link? All data will be lost."),
            Form(
                Input(
                    type="submit",
                    value="Yes, delete",
                ),
                Input(
                    type="hidden",
                    name="redirect",
                    value=redirect,
                ),
                action=f"{link.url}/delete",
                method="POST",
            ),
            Form(
                Input(
                    type="submit",
                    value="Cancel",
                    cls="secondary",
                ),
                action=request.headers["Referer"],
                method="GET",
            ),
            cls="container",
        ),
    )


@rt("/{link:Item}/delete")
def post(link: items.Item, redirect: str):
    "Actually delete the link."
    assert isinstance(link, items.Link)
    link.delete()
    return components.redirect(redirect)
