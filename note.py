"Note entry pages."

from fasthtml.common import *
import marko

import components
import constants
import entries


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
            Form(
                Input(
                    type="submit",
                    value="Cancel",
                    cls="secondary",
                ),
                action=request.headers.get("Referer", "/"),
                method="GET",
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
    note.text = text.strip()
    note.write()
    entries.set_keywords_relations(note)
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
                    Li(
                        components.get_nav_menu(
                            A(Strong("Edit"), href=f"{note.url}/edit"),
                            A(Strong("Copy"), href=f"{note.url}/copy"),
                            A(Strong("Delete"), href=f"{note.url}/delete"),
                        )
                    ),
                    Li(components.get_entry_clipboard(note), note.title),
                    Li(components.search_form()),
                ),
                cls="note",
            ),
            cls="container",
        ),
        Main(
            NotStr(marko.convert(note.text)),
            Small(
                Card(
                    Header("Keywords: ", components.get_keywords_links(note)),
                    components.get_entries_table(note.related()),
                ),
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
    )


@rt("/{note:Entry}/edit")
def get(note: entries.Entry):
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
                Fieldset(
                    Label(
                        "Title",
                        Input(
                            type="text",
                            name="title",
                            value=note.title,
                            required=True,
                        ),
                    ),
                    Label(
                        "Text",
                        Textarea(
                            note.text,
                            name="text",
                            rows=10,
                            autofocus=True,
                        ),
                    ),
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
def post(note: entries.Entry, title: str, text: str):
    "Actually edit the note."
    assert isinstance(note, entries.Note)
    note.title = title or "no title"
    note.text = text
    note.write()
    entries.set_keywords_relations(note)
    return components.redirect(note.url)


@rt("/{note:Entry}/copy")
def get(note: entries.Entry):
    "Form for making a copy of the note."
    assert isinstance(note, entries.Note)
    return (
        Title("Copy"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Copy '{note.title}')"),
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
                ),
                Textarea(
                    note.text,
                    name="text",
                    rows=10,
                    autofocus=True,
                ),
                Input(
                    type="submit",
                    value="Save",
                ),
                action=f"/note/",
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
def get(note: entries.Entry):
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
    )


@rt("/{note:Entry}/delete")
def post(note: entries.Entry, action: str):
    "Actually delete the note."
    assert isinstance(note, entries.Note)
    if "yes" in action.casefold():
        note.delete()
        return components.redirect(f"/")
    else:
        return components.redirect(note.url)
