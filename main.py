"Chaos notebook."

from icecream import install
install()

from fasthtml.common import *
import marko

import components
import constants
import entries


class EntryConvertor(Convertor):
    regex = "[^./]+"

    def convert(self, value: str) -> entries.Entry:
        return entries.get(value)

    def to_string(self, value: entries.Entry) -> str:
        return str(value)

register_url_convertor("Entry", EntryConvertor())


entries.read_entry_files()

app, rt = fast_app(
    live=True,
    static_path="static",
    hdrs=(Link(rel="stylesheet", href="/mods.css", type="text/css")),
)

@rt
def index():
    return [
        Title("chaos"),
        Script(src="/clipboard.min.js"),
        Script("new ClipboardJS('.to_clipboard');"),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
                    Li(components.search_form()),
                ),
                Ul(
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
                style=constants.NAV_STYLE,
            ),
            cls="container",
        ),
        Main(
            Table(
                Tbody(
                    *[Tr(Td(components.get_entry_clipboard(entry)),
                         Td(components.entry_icon(entry)),
                         Td(A(entry.title, href=f"/entry/{entry}")),
                         Td(entry.size, style="text-align: right;"),
                         Td(entry.modified_local),
                         )
                      for entry in entries.recent(0, 25)
                      ]
                ),
                cls="striped",
            ),
            cls="container",
        ),
        Footer(
            Hr(),
            Small(f"v {constants.VERSION}"),
            cls="container",
        )
    ]


@rt("/entry/{entry:Entry}")
def get(entry: entries.Entry):
    "Display entry."
    return [
        Title(entry.title),
        Script(src="/clipboard.min.js"),
        Script("new ClipboardJS('.to_clipboard');"),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
                    Li(components.get_entry_clipboard(entry)),
                    Li("Note"),
                    Li(Strong(entry.title)),
                    Li(A(
                        "Edit",
                        role="button",
                        href=f"/edit/{entry}")),
                    Li(A(
                        "Copy",
                        role="button",
                        href=f"/copy/{entry}")),
                    Li(A(
                        "Delete",
                        role="button",
                        href=f"/delete/{entry}",
                        cls="outline")),
                ),
                Ul(
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
                style=constants.NAV_STYLE,
            ),
            cls="container",
        ),
        Main(
            NotStr(marko.convert(entry.content)),
            cls="container",
        ),
        Footer(
            Hr(),
            Div(
                Small(f"{entry.size} bytes"),
                Small(entry.modified_local),
                cls="grid",
            ),
            cls="container",
        )
    ]


@rt("/copy/{entry:Entry}")
def copy(entry:entries.Entry):
    "Copy the entry."
    return Redirect(f"/entry/{entry.copy()}")


@rt("/delete/{entry:Entry}")
def get(entry:entries.Entry):
    "Ask for confirmation to delete the entry."
    return [
        Title(entry.title),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
                    Li("Note"),
                    Li(Strong(entry.title)),
                ),
                style=constants.NAV_STYLE,
            ),
            cls="container",
        ),
        Main(
            P("Really delete the entry? All data will be lost."),
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
                action=f"/delete/{entry}",
                method="POST",
            ),
            cls="container",
        ),
        Footer(
            Hr(),
            Div(
                Small(f"{entry.size} bytes"),
                Small(entry.modified_local),
                cls="grid",
            ),
            cls="container",
        )
    ]


@rt("/delete/{entry:Entry}")
def post(entry:entries.Entry, action:str):
    "Actually delete the entry."
    if "yes" in action.casefold():
        entry.delete()
        return Redirect(f"/")
    else:
        return Redirect(f"/entry/{entry}")


@rt("/note")
def get():
    "Form for adding a note."
    return [
        Title("chaos"),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
                    Li("Add note"),
                ),
                style=constants.NAV_STYLE,
            ),
            cls="container",
        ),
        Main(
            Form(
                Input(
                    type="text",
                    name="title",
                    placeholder="Title (required)...",
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
                action="/note",
                method="POST",
            ),
            cls="container",
        ),
    ]

@rt("/note")
def post(title:str, text:str):
    "Actually add the note."
    entry = entries.create_entry(title)
    entry.content = text
    entry.write()
    return Redirect(f"/entry/{entry}")

@rt("/edit/{entry:Entry}")
def get(entry: entries.Entry):
    "Form for editing an entry."
    match entry.type:
        case constants.NOTE:
            fields = [
                Input(
                    type="text",
                    name="title",
                    value=entry.title,
                ),
                Textarea(
                    entry.content,
                    name="text",
                    rows=10,
                    autofocus=True,
                ),
            ]
        case constants.LINK:
            raise NotImplementedError
        case constants.FILE:
            raise NotImplementedError
        case _:
            raise NotImplementedError
    return [
        Title("chaos"),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
                    Li(f"Edit {entry.type}"),
                    Li(Strong(entry.title)),
                ),
                style=constants.NAV_STYLE,
            ),
            cls="container",
        ),
        Main(
            Form(
                *fields,
                Input(
                    type="submit",
                    value="Save",
                ),
                action=f"/edit/{entry}",
                method="POST",
            ),
            Form(
                Input(
                    type="submit",
                    value="Cancel",
                    cls="secondary",
                ),
                action=f"/entry/{entry}",
                method="GET",
            ),
            cls="container",
        ),
    ]

@rt("/edit/{entry:Entry}")
def post(entry:entries.Entry, title:str, text:str):
    "Actually edit the entry."
    match entry.type:
        case constants.NOTE:
            entry.title = title or "[no title]"
            entry.content = text
        case constants.LINK:
            raise NotImplementedError
        case constants.FILE:
            raise NotImplementedError
        case _:
            raise NotImplementedError
    entry.write()
    return Redirect(f"/entry/{entry}")


@rt("/search")
def get():
    "Search the entries."
    raise NotImplementedError


serve(port=5002)
