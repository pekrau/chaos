"Note entry pages."

from fasthtml.common import *
import marko

import components
import constants
import entries
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
                    Li("Add note"),
                ),
                cls="note",
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
                    cls="grid",
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
                action="/note/",
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
def post(session, title: str, text: str, keywords: list[str] = None):
    "Actually add the note."
    note = entries.Note()
    # XXX For some reason, 'auth' is not set in 'request.scope'?
    note.owner = session["auth"]
    note.title = title.strip() or "no title"
    note.text = text.strip()
    note.keywords = keywords or list()
    note.write()
    return components.redirect(note.url)


@rt("/{note:Entry}")
def get(note: entries.Entry):
    "View the note."
    assert isinstance(note, entries.Note)
    return (
        Title(note.title),
        Script(src="/clipboard.min.js"),
        Script("new ClipboardJS('.to_clipboard');"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(Strong(note.title)),
                    Li(*components.get_entry_links(note)),
                ),
                Ul(Li(components.search_form())),
                cls="note",
            ),
            cls="container",
        ),
        Main(
            NotStr(marko.convert(note.text)),
            components.get_keywords_entries_card(note),
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
    )


@rt("/{note:Entry}/edit")
def get(request, note: entries.Entry):
    "Form for editing a note."
    assert isinstance(note, entries.Note)
    return (
        Title("Edit"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Edit '{note.title}'"),
                ),
                cls="note",
            ),
            cls="container",
        ),
        Main(
            Form(
                Div(
                    Input(
                        type="text",
                        name="title",
                        value=note.title,
                        placeholder="Title...",
                        required=True,
                    ),
                    Details(
                        Summary("Keywords..."),
                        Ul(*components.get_keywords_dropdown(note.keywords)),
                        cls="dropdown",
                    ),
                    cls="grid",
                ),
                Textarea(
                    note.text,
                    name="text",
                    rows=10,
                    placeholder="Text...",
                    autofocus=True,
                ),
                Input(
                    type="submit",
                    value="Save",
                ),
                action=f"{note.url}/edit",
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


@rt("/{note:Entry}/edit")
def post(note: entries.Entry, title: str, text: str, keywords: list[str] = None):
    "Actually edit the note."
    assert isinstance(note, entries.Note)
    note.title = title or "no title"
    note.text = text.strip()
    note.keywords = keywords or list()
    note.write()
    return components.redirect(note.url)


@rt("/{note:Entry}/copy")
def get(request, note: entries.Entry):
    "Form for making a copy of the note."
    assert isinstance(note, entries.Note)
    return (
        Title("Copy"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Copy '{note.title}'"),
                ),
                cls="note",
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
                    value="Copy",
                ),
                action=f"{note.url}/copy",
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


@rt("/{source:Entry}/copy")
def post(session, source: entries.File, title: str):
    "Actually copy the note."
    assert isinstance(source, entries.Note)
    note = entries.Note()
    # XXX For some reason, 'auth' is not set in 'request.scope'?
    note.owner = session["auth"]
    note.title = title.strip()
    note.text = source.text
    note.keywords = source.keywords
    note.write()
    return components.redirect(note.url)


@rt("/{note:Entry}/delete")
def get(request, note: entries.Entry):
    "Ask for confirmation to delete the note."
    assert isinstance(note, entries.Note)
    return (
        Title("Delete"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Delete '{note.title}'"),
                ),
                cls="note",
            ),
            cls="container",
        ),
        Main(
            P("Really delete the note? All data will be lost."),
            Form(
                Input(
                    type="submit",
                    value="Yes, delete",
                ),
                Input(
                    type="hidden",
                    name="target",
                    value=request.headers["Referer"],
                ),
                action=f"{note.url}/delete",
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


@rt("/{note:Entry}/delete")
def post(note: entries.Entry, target: str):
    "Actually delete the note."
    assert isinstance(note, entries.Note)
    note.delete()
    return components.redirect(target)
