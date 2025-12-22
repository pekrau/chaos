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
                Fieldset(
                    Input(
                        type="text",
                        name="title",
                        placeholder="Title...",
                        required=True,
                        autofocus=True,
                    ),
                    Details(
                        Summary("Keywords..."),
                        Ul(*components.get_keywords_dropdown(keywords=[])),
                        cls="dropdown",
                    ),
                    cls="grid",
                ),
                Fieldset(
                    Textarea(
                        name="text",
                        rows=10,
                        placeholder="Text...",
                    ),
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
def post(session, title: str, text: str, keywords: list[str] = []):
    "Actually add the note."
    note = entries.Note()
    # XXX For some reason, 'auth' is not set in 'request.scope'?
    note.owner = session["auth"]
    note.title = title.strip() or "no title"
    note.text = text.strip()
    note.keywords = keywords
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
                    Li(
                        components.get_nav_menu(
                            A(Strong("Edit"), href=f"{note.url}/edit"),
                            A(Strong("Copy"), href=f"{note.url}/copy"),
                            A(Strong("Delete"), href=f"{note.url}/delete"),
                        )
                    ),
                    Li(
                        components.get_entry_link_to_clipboard(note),
                        components.get_entry_edit(note),
                    ),
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
                Fieldset(
                    Textarea(
                        note.text,
                        name="text",
                        rows=10,
                        placeholder="Text...",
                        autofocus=True,
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
def post(note: entries.Entry, title: str, text: str, keywords: list[str] = []):
    "Actually edit the note."
    assert isinstance(note, entries.Note)
    note.title = title or "no title"
    note.text = text.strip()
    note.keywords = keywords
    note.write()
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
                Fieldset(
                    Input(
                        type="text",
                        name="title",
                        value=note.title,
                        placeholder="Title...",
                        required=True,
                        autofocus=True,
                    ),
                ),
                Input(
                    type="submit",
                    value="Copy",
                ),
                action=f"/note/{note}/copy",
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
