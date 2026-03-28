"Note item pages."

import urllib.parse

from fasthtml.common import *

import components
import constants
import items

app, rt = components.get_app_rt()


@rt("/")
def get(form: dict):
    "Form for adding a note."
    title = "Add note"
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
                components.get_title_input(form.get("title", "")),
                components.get_text_input(),
                components.get_tags_input(),
                Input(type="hidden", name="id", value=form.get("title", "")),
                Input(type="submit", value="Add note"),
                action="/note/",
                method="POST",
            ),
            components.get_cancel_form("/"),
            cls="container",
        ),
    )


@rt("/")
def post(title: str, text: str, id: str = "", tags: list[str] = None):
    "Actually add the note."
    if id:
        note = items.Note(constants.DATA_DIR / f"{id}.md")
        items.lookup[note.id] = note
    else:
        note = items.Note()
    note.title = title.strip() or "no title"
    note.text = text.strip()
    note.tags = tags
    note.write()
    return components.redirect(note.url)


@rt("/{note:Item}")
def get(note: items.Item):
    "View the note."
    assert isinstance(note, items.Note)
    return (
        Title(note.title),
        components.clipboard_script(),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(note)),
                    Li(components.get_note_icon(), note.title),
                    Li(components.to_clipboard(note)),
                ),
                Ul(
                    Li(components.get_shortcuts_menu(note)),
                ),
            ),
            cls="container",
        ),
        Main(
            components.get_text_card(note),
            components.get_tags_card(note),
            components.get_refs_card(note),
            cls="container",
        ),
        Footer(
            Hr(),
            Div(
                Div(note.modified_local),
                Div(f"{note.size} bytes"),
                Div(A("Source", href=f"/source/{note.id}"), cls="right"),
                cls="grid",
            ),
            cls="container",
        ),
        components.clipboard_activate(),
    )


@rt("/{note:Item}/edit")
def get(request, note: items.Item):
    "Form for editing a note."
    assert isinstance(note, items.Note)
    title = f"Edit '{note.title}'"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(note)),
                    Li(title),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                components.get_title_input(note.title),
                components.get_text_input(note.text),
                components.get_tags_input(note.tags),
                Input(type="submit", value="Save"),
                action=f"{note.url}/edit",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/{note:Item}/edit")
def post(note: items.Item, title: str, text: str, tags: list[str] = None):
    "Actually edit the note."
    assert isinstance(note, items.Note)
    note.title = title.strip()
    note.text = text.strip()
    note.tags = tags
    note.write()
    return components.redirect(note.url)


@rt("/{note:Item}/copy")
def get(request, note: items.Item):
    "Form for making a copy of the note."
    assert isinstance(note, items.Note)
    title = f"Copy '{note.title}'"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(note)),
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
                    value=note.title,
                    placeholder="Title...",
                    required=True,
                ),
                Input(type="submit", value="Copy note"),
                action=f"{note.url}/copy",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/{source:Item}/copy")
def post(source: items.File, title: str):
    "Actually copy the note."
    assert isinstance(source, items.Note)
    note = items.Note()
    note.title = title.strip()
    note.text = source.text
    note.write()
    return components.redirect(note.url)


@rt("/{note:Item}/delete")
def get(request, note: items.Item):
    "Ask for confirmation to delete the note."
    assert isinstance(note, items.Note)
    redirect = urllib.parse.urlsplit(request.headers["Referer"]).path
    if redirect == f"/note/{note.id}":
        redirect = "/"
    title = f"Delete '{note.title}'"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(note)),
                    Li(title),
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
                Input(type="submit", value="Yes, delete"),
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
