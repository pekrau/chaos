"Link item pages."

import urllib.parse

from fasthtml.common import *

import components
import constants
import items

app, rt = components.get_app_rt()


@rt("/")
def get():
    "Form for adding a link."
    title = "Add link"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(title),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                components.get_title_input(),
                Input(type="href", name="href", placeholder="Href...", required=True),
                components.get_text_input(),
                components.get_tags_input(),
                Input(type="submit", value="Add link"),
                action="/link/",
                method="POST",
            ),
            components.get_cancel_form("/"),
            cls="container",
        ),
    )


@rt("/")
def post(title: str, href: str, text: str, tags: list[str] = None):
    "Actually add the link."
    link = items.Link()
    link.title = title.strip() or "no title"
    link.href = href.strip() or "/"
    link.text = text.strip()
    link.tags = tags
    link.write()
    return components.redirect(link.url)


@rt("/{link:Item}")
def get(link: items.Item, page: int = 1, tags_page: int = 1, refs_page: int = 1):
    "View the data for the link."
    assert isinstance(link, items.Link)
    return (
        Title(link.title),
        components.get_clipboard_script(),
        components.get_header_item_view(link),
        Main(
            Card(Strong(A(link.href, href=link.href, target="_blank"))),
            components.get_text_card(link),
            Form(
                components.get_tags_card(link, tags_page),
                components.get_refs_card(link, refs_page),
                action=link.url,
            ),
            cls="container",
        ),
        components.get_footer_item_view(link),
        components.get_clipboard_activate(),
    )


@rt("/{link:Item}/edit")
def get(request, link: items.Item):
    "Form for editing a link."
    assert isinstance(link, items.Link)
    return (
        *components.get_header_item_edit(link),
        Main(
            Form(
                components.get_title_input(link.title),
                Input(
                    type="href",
                    name="href",
                    value=link.href,
                    placeholder="Href...",
                    required=True,
                ),
                components.get_text_input(link.text),
                components.get_tags_input(link.tags),
                Input(type="submit", value="Save"),
                action=f"{link.url}/edit",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/{link:Item}/edit")
def post(link: items.Item, title: str, href: str, text: str, tags: list[str] = None):
    "Actually edit the link."
    assert isinstance(link, items.Link)
    link.title = title.strip()
    link.href = href.strip() or "/"
    link.text = text.strip()
    link.tags = tags
    link.write()
    return components.redirect(link.url)


@rt("/{link:Item}/copy")
def get(request, link: items.Item):
    "Form for making a copy of the link."
    assert isinstance(link, items.Link)
    title = f"Copy '{link.title}'"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(link)),
                    Li(title),
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
def post(source: items.File, title: str):
    "Actually copy the link."
    assert isinstance(source, items.Link)
    link = items.Link()
    link.title = title.strip()
    link.href = source.href
    link.text = source.text
    link.write()
    return components.redirect(link.url)


@rt("/{link:Item}/delete")
def get(request, link: items.Item):
    "Ask for confirmation to delete the link."
    assert isinstance(link, items.Link)
    redirect = urllib.parse.urlsplit(request.headers["Referer"]).path
    if redirect == f"/link/{link.id}":
        redirect = "/"
    title = f"Delete {link.title}"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(link)),
                    Li(title),
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
