"Note item pages."

import urllib.parse

from fasthtml.common import *

import components
import constants
import items
import settings

app, rt = components.get_app_rt()


@rt("/")
def get(request):
    "Form for adding a note."
    return (
        Title("Add note"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(components.get_note_icon(), "Add note"),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                components.get_title_input(None),
                components.get_text_input(None),
                components.get_listset_keyword_inputs(None),
                Input(type="submit", value="Add note"),
                action="/note/",
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
    text: str,
    listsets: list[str] = None,
    keywords: list[str] = None,
):
    "Actually add the note."
    note = items.Note()
    note.owner = request.scope["auth"]
    note.title = title.strip() or "no title"
    note.text = text.strip()
    for id in listsets or list():
        listset = items.get(id)
        assert isinstance(listset, items.Listset)
        listset.add(note)
        listset.write()
    note.keywords = keywords or list()
    note.write()
    return components.redirect(note.url)


@rt("/{note:Item}")
def get(note: items.Item):
    "View the note."
    assert isinstance(note, items.Note)
    return (
        Title(note.title),
        Script(src="/clipboard.min.js"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(components.get_note_icon(), note.title),
                    Li(*components.get_item_links(note)),
                ),
                Ul(Li(components.search_form())),
            ),
            cls="container",
        ),
        Main(
            components.get_text_card(note),
            Div(
                components.get_listsets_card(note),
                components.get_keywords_card(note),
                cls="grid",
            ),
            cls="container",
        ),
        Footer(
            Hr(),
            Div(
                Div(note.modified_local),
                Div(f"{note.size} bytes"),
                Div(note.owner),
                cls="grid",
            ),
            cls="container",
        ),
        Script("new ClipboardJS('.to_clipboard');", type="text/javascript"),
    )


@rt("/{note:Item}/edit")
def get(request, note: items.Item):
    "Form for editing a note."
    assert isinstance(note, items.Note)
    return (
        Title(f"Edit {note.title}"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(Strong("Edit "), note.title),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                components.get_title_input(note),
                components.get_text_input(note),
                components.get_listset_keyword_inputs(note),
                Input(type="submit", value="Save"),
                action=f"{note.url}/edit",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/{note:Item}/edit")
def post(
    note: items.Item,
    title: str,
    text: str,
    listsets: list[str] = None,
    keywords: list[str] = None,
):
    "Actually edit the note."
    assert isinstance(note, items.Note)
    note.title = title or "no title"
    note.text = text.strip()
    for id in listsets or list():
        listset = items.get(id)
        assert isinstance(listset, items.Listset)
        listset.add(note)
        listset.write()
    note.keywords = keywords or list()
    note.write()
    return components.redirect(note.url)


@rt("/{note:Item}/copy")
def get(request, note: items.Item):
    "Form for making a copy of the note."
    assert isinstance(note, items.Note)
    return (
        Title("Copy"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Copy '{note.title}'"),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                Input(
                    type="text",
                    name="title",
                    value=note.title,
                    placeholder="Title...",
                    required=True,
                    autofocus=True,
                ),
                Input(
                    type="submit",
                    value="Copy note",
                ),
                action=f"{note.url}/copy",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/{source:Item}/copy")
def post(request, source: items.File, title: str):
    "Actually copy the note."
    assert isinstance(source, items.Note)
    note = items.Note()
    note.owner = request.scope["auth"]
    note.title = title.strip()
    note.text = source.text
    note.keywords = source.keywords
    note.write()
    return components.redirect(note.url)


@rt("/{note:Item}/delete")
def get(request, note: items.Item):
    "Ask for confirmation to delete the note."
    assert isinstance(note, items.Note)
    redirect = urllib.parse.urlsplit(request.headers["Referer"]).path
    if redirect == f"/note/{note.id}":
        redirect = "/notes"
    return (
        Title(f"Delete {note.title}"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(Strong("Delete "), note.title),
                ),
            ),
            cls="container",
        ),
        Main(
            H3("Really delete the note? All data will be lost."),
            Form(
                Input(
                    type="hidden",
                    name="redirect",
                    value=redirect,
                ),
                Input(
                    type="submit",
                    value="Yes, delete",
                ),
                action=f"{note.url}/delete",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/{note:Item}/delete")
def post(note: items.Item, redirect: str):
    "Actually delete the note."
    assert isinstance(note, items.Note)
    note.delete()
    return components.redirect(redirect)
