"Tag item pages."

import urllib.parse

from fasthtml.common import *

import components
import constants
import items

app, rt = components.get_app_rt()


@rt("/")
def get():
    "Form for adding a tag."
    title = "Add tag"
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
                components.get_text_input(),
                components.get_tags_input(),
                Input(type="submit", value="Add tag"),
                action="/tag/",
                method="POST",
            ),
            components.get_cancel_form("/"),
            cls="container",
        ),
    )


@rt("/")
def post(title: str, text: str, id: str = "", tags: list[str] = None):
    "Actually add the tag."
    if id:
        tag = items.Tag(constants.DATA_DIR / f"{id}.md")
        items.lookup[tag.id] = tag
    else:
        tag = items.Tag()
    tag.title = title.strip() or "no title"
    tag.text = text.strip()
    tag.tags = tags
    tag.write()
    return components.redirect(tag.url)


@rt("/{tag:Item}")
def get(tag: items.Item, page: int = 1, tags_page: int = 1, refs_page: int = 1):
    "View the tag."
    assert isinstance(tag, items.Tag)
    items_list = tag.tagged
    items_list.sort(key=lambda i: i.modified, reverse=True)
    return (
        Title(tag.title),
        components.get_clipboard_script(),
        components.get_header_item_view(tag),
        Main(
            components.get_text_card(tag),
            Form(
                Card(
                    Header("Tagged..."),
                    components.get_items_display(items_list, page=page),
                ),
                components.get_refs_card(tag, refs_page),
                components.get_tags_card(tag, tags_page),
                action=tag.url,
            ),
            cls="container",
        ),
        components.get_footer_item_view(tag),
        components.get_clipboard_activate(),
    )


@rt("/{tag:Item}/edit")
def get(tag: items.Item):
    "Form for editing a tag."
    assert isinstance(tag, items.Tag)
    return (
        *components.get_header_item_edit(tag),
        Main(
            Form(
                components.get_title_input(tag.title),
                components.get_text_input(tag.text),
                components.get_tags_input(tag.tags, tag=tag),
                Input(type="submit", value="Save"),
                action=f"{tag.url}/edit",
                method="POST",
            ),
            components.get_cancel_form(tag.url),
            cls="container",
        ),
    )


@rt("/{tag:Item}/edit")
def post(tag: items.Item, title: str, text: str, tags: list[str] = None):
    "Actually edit the tag."
    assert isinstance(tag, items.Tag)
    tag.title = title.strip()
    tag.text = text.strip()
    tag.tags = tags
    tag.write()
    return components.redirect(tag.url)


@rt("/{tag:Item}/copy")
def get(tag: items.Item):
    "Form for making a copy of the tag."
    assert isinstance(tag, items.Tag)
    title = f"Copy '{tag.title}'"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(tag)),
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
                    value=tag.title,
                    placeholder="Title...",
                    required=True,
                ),
                Input(type="submit", value="Copy tag"),
                action=f"{tag.url}/copy",
                method="POST",
            ),
            components.get_cancel_form(tag.url),
            cls="container",
        ),
    )


@rt("/{source:Item}/copy")
def post(source: items.File, title: str):
    "Actually copy the tag."
    assert isinstance(source, items.Tag)
    tag = items.Tag()
    tag.title = title.strip()
    tag.text = source.text
    tag.write()
    return components.redirect(tag.url)


@rt("/{tag:Item}/delete")
def get(tag: items.Item):
    "Ask for confirmation to delete the tag."
    assert isinstance(tag, items.Tag)
    title = f"Delete '{tag.title}'"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(tag)),
                    Li(title),
                ),
            ),
            cls="container",
        ),
        Main(
            H3("Really delete the tag? All data will be lost."),
            Form(
                Input(type="submit", value="Yes, delete"),
                action=f"{tag.url}/delete",
                method="POST",
            ),
            components.get_cancel_form(tag.url),
            cls="container",
        ),
    )


@rt("/{tag:Item}/delete")
def post(tag: items.Item):
    "Actually delete the tag."
    assert isinstance(tag, items.Tag)
    tag.delete()
    return components.redirect()
