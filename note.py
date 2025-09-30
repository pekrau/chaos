"Note entry pages."

from fasthtml.common import *
import marko

import components
import constants
import entries


app, rt = components.fast_app()


@rt("/")
def get(session):
    "Form for adding a note."
    return (
        Title("chaos"),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
                    Li("Add note"),
                ),
                style=constants.NOTE_NAV_STYLE,
            ),
            cls="container",
        ),
        Main(
            Form(
                Input(
                    type="text",
                    name="title",
                    placeholder="Title...",
                    required=True,
                    autofocus=True,
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
            cls="container",
        ),
    )


@rt("/")
def post(session, title: str, text: str):
    "Actually add the note."
    note = entries.Note()
    # XXX For some reason, 'auth' is not set in 'request.scope'?
    note.owner = session["auth"]
    note.title = title.strip() or "no title"
    note.content = text.strip()
    note.write()
    return Redirect(note.url)


@rt("/{note:Entry}")
def get(session, note: entries.Entry):
    "View the note."
    assert isinstance(note, entries.Note)
    return (
        Title(note.title),
        Script(src="/clipboard.min.js"),
        Script("new ClipboardJS('.to_clipboard');"),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
                    Li(components.get_entry_clipboard(note)),
                    Li(Strong(note.title)),
                    Li(A("Edit", role="button", href=f"{note.url}/edit")),
                    Li(A("Copy", role="button", href=f"{note.url}/copy")),
                    Li(
                        A(
                            "Delete",
                            role="button",
                            href=f"{note.url}/delete",
                            cls="outline",
                        )
                    ),
                ),
                Ul(
                    Li(components.search_form()),
                    Li(
                        Details(
                            Summary("Add..."),
                            Ul(
                                Li(A("Note", href="/note")),
                                Li(A("Link", href="/link")),
                                Li(A("File", href="/file")),
                            ),
                            cls="dropdown",
                        ),
                    ),
                ),
                style=constants.NOTE_NAV_STYLE,
            ),
            cls="container",
        ),
        Main(
            NotStr(marko.convert(note.content)),
            Small(
                Card(
                    Header(
                        "Keywords: ",
                        ", ".join(sorted(note.keywords)),
                    ),
                    components.get_entries_table(note.related()),
                ),
            ),
            cls="container",
        ),
        Footer(
            Hr(),
            Div(
                Div(f"{note.size} bytes"),
                Div(note.modified_local),
                cls="grid",
            ),
            cls="container",
        ),
    )


@rt("/{note:Entry}/edit")
def get(session, note: entries.Entry):
    "Form for editing a note."
    assert isinstance(note, entries.Note)
    return (
        Title("chaos"),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
                    Li(f"Edit note"),
                    Li(Strong(note.title)),
                ),
                style=constants.NOTE_NAV_STYLE,
            ),
            cls="container",
        ),
        Main(
            Form(
                Input(
                    type="text",
                    name="title",
                    value=note.title,
                    required=True,
                ),
                Textarea(
                    note.content,
                    name="text",
                    rows=10,
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
                action=note.url,
                method="GET",
            ),
            cls="container",
        ),
    )


@rt("/{note:Entry}/edit")
def post(session, note: entries.Entry, title: str, text: str):
    "Actually edit the note."
    assert isinstance(note, entries.Note)
    note.title = title or "no title"
    note.content = text
    note.write()
    return Redirect(note.url)


@rt("/{note:Entry}/copy")
def get(session, note: entries.Entry):
    "Form for making a copy of the note."
    assert isinstance(note, entries.Note)
    return (
        Title("chaos"),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
                    Li("Copy note"),
                    Li(Strong(note.title)),
                ),
                style=constants.NOTE_NAV_STYLE,
            ),
            cls="container",
        ),
        Main(
            Form(
                Input(
                    type="text",
                    name="title",
                    value=note.title,
                ),
                Textarea(
                    note.content,
                    name="text",
                    rows=10,
                    autofocus=True,
                ),
                Input(
                    type="submit",
                    value="Save",
                ),
                action=f"/note",
                method="POST",
            ),
            Form(
                Input(
                    type="submit",
                    value="Cancel",
                    cls="secondary",
                ),
                action=note.url,
                method="GET",
            ),
            cls="container",
        ),
    )


@rt("/{note:Entry}/delete")
def get(session, note: entries.Entry):
    "Ask for confirmation to delete the note."
    assert isinstance(note, entries.Note)
    return (
        Title(note.title),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
                    Li("Note"),
                    Li(Strong(note.title)),
                ),
                style=constants.NOTE_NAV_STYLE,
            ),
            cls="container",
        ),
        Main(
            P("Really delete the note? All data will be lost."),
            Form(
                Fieldset(
                    Input(
                        type="submit",
                        name="action",
                        value="Yes, delete",
                    ),
                    Input(
                        type="submit",
                        name="action",
                        value="Cancel",
                        cls="secondary",
                    ),
                ),
                action=f"{note.url}/delete",
                method="POST",
            ),
            cls="container",
        ),
        Footer(
            Hr(),
            Div(
                Div(f"{note.size} bytes"),
                Div(note.modified_local),
                cls="grid",
            ),
            cls="container",
        ),
    )


@rt("/{note:Entry}/delete")
def post(session, note: entries.Entry, action: str):
    "Actually delete the note."
    assert isinstance(note, entries.Note)
    if "yes" in action.casefold():
        note.delete()
        entries.set_all_keywords_relations()
        return Redirect(f"/")
    else:
        return Redirect(note.url)
