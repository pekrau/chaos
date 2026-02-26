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
                components.get_title_input(None),
                Input(type="href", name="href", placeholder="Href...", required=True),
                components.get_text_input(None),
                components.get_listset_keyword_inputs(None),
                Input(type="submit", value="Add link"),
                action="/link/",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/")
def post(
    request,
    title: str,
    href: str,
    text: str,
    keywords: list[str] = None,
    listsets: list[str] = None,
):
    "Actually add the link."
    link = items.Link()
    link.owner = request.scope["auth"]
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
    "View the data for the link."
    assert isinstance(link, items.Link)
    return (
        Title(link.title),
        Script(src="/clipboard.min.js"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(components.get_link_icon(), link.title),
                    Li(*components.get_item_links(link)),
                ),
                Ul(Li(components.search_form())),
            ),
            cls="container",
        ),
        Main(
            Card(
                A(
                    link.href,
                    href=link.href,
                    target="_blank",
                )
            ),
            components.get_text_card(link),
            Div(
                components.get_listsets_card(link),
                components.get_keywords_card(link),
                cls="grid",
            ),
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
        Script("new ClipboardJS('.to_clipboard');", type="text/javascript"),
    )


@rt("/{link:Item}/edit")
def get(request, link: items.Item):
    "Form for editing a link."
    assert isinstance(link, items.Link)
    return (
        Title(f"Edit {link.title}"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(Strong("Edit "), link.title),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                components.get_title_input(link),
                Input(
                    type="href",
                    name="href",
                    value=link.href,
                    placeholder="Href...",
                    required=True,
                ),
                components.get_text_input(link),
                components.get_listset_keyword_inputs(link),
                Input(type="submit", value="Save"),
                action=f"{link.url}/edit",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/{link:Item}/edit")
def post(
    link: items.Item,
    title: str,
    href: str,
    text: str,
    listsets: list[str] = None,
    keywords: list[str] = None,
):
    "Actually edit the link."
    assert isinstance(link, items.Link)
    link.edit(title, text, listsets, keywords)
    link.href = href.strip() or "/"
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
                Input(type="submit", value="Copy link"),
                action=f"{link.url}/copy",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/{source:Item}/copy")
def post(request, source: items.File, title: str):
    "Actually copy the link."
    assert isinstance(source, items.Link)
    link = items.Link()
    link.owner = request.scope["auth"]
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
        Title(f"Delete {link.title}"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(Strong("Delete "), link.title),
                ),
            ),
            cls="container",
        ),
        Main(
            H3("Really delete the link? All data will be lost."),
            Form(
                Input(
                    type="hidden",
                    name="redirect",
                    value=redirect,
                ),
                Input(type="submit", value="Yes, delete"),
                action=f"{link.url}/delete",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/{link:Item}/delete")
def post(link: items.Item, redirect: str):
    "Actually delete the link."
    assert isinstance(link, items.Link)
    link.delete()
    return components.redirect(redirect)
