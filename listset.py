"Listset (ordered set) entry pages."

from fasthtml.common import *
import marko

import components
import constants
import entries


app, rt = components.get_app_rt()


@rt("/")
def get(request):
    "Form for adding an listset."
    return (
        Title("Add listset"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li("Add listset"),
                ),
                cls="listset",
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
                        Ul(*components.get_keywords_dropdown(keywords=list())),
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
                action="/listset/",
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
    "Actually add the listset."
    listset = entries.Listset()
    # XXX For some reason, 'auth' is not set in 'request.scope'?
    listset.owner = session["auth"]
    listset.title = title.strip() or "no title"
    listset.text = text.strip()
    listset.keywords = keywords or list()
    listset.frontmatter["items"] = list()
    listset.write()
    return components.redirect(listset.url)


@rt("/{listset:Entry}")
def get(listset: entries.Entry):
    "View the metadata for the listset."
    assert isinstance(listset, entries.Listset)
    return (
        Title(listset.title),
        Script(src="/clipboard.min.js"),
        Script("new ClipboardJS('.to_clipboard');"),
        Header(
            Nav(
                Ul(
                    Li(
                        components.get_nav_menu(
                            A(Strong("Edit"), href=f"{listset.url}/edit"),
                            A(Strong("Copy"), href=f"{listset.url}/copy"),
                            A(Strong("Delete"), href=f"{listset.url}/delete"),
                        )
                    ),
                    Li(Strong(listset.title)),
                    Li(*components.get_entry_links(listset)),
                ),
                Ul(Li(components.search_form())),
                cls="listset",
            ),
            cls="container",
        ),
        Main(
            NotStr(marko.convert(listset.text)),
            Card("List of items..."),
            components.get_keywords_entries_card(listset),
            cls="container",
        ),
        Footer(
            Hr(),
            Div(
                Div(listset.modified_local),
                Div(f"{listset.size} bytes"),
                Div(listset.owner),
                cls="grid",
            ),
            cls="container",
        ),
    )


@rt("/{listset:Entry}/edit")
def get(request, listset: entries.Entry):
    "Form for editing a listset."
    assert isinstance(listset, entries.Listset)
    return (
        Title("Edit"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Edit '{listset.title}'"),
                ),
                cls="listset",
            ),
            cls="container",
        ),
        Main(
            Form(
                Fieldset(
                    Input(
                        type="text",
                        name="title",
                        value=listset.title,
                        placeholder="Title...",
                        required=True,
                    ),
                    Details(
                        Summary("Keywords..."),
                        Ul(*components.get_keywords_dropdown(listset.keywords)),
                        cls="dropdown",
                    ),
                    cls="grid",
                ),
                Fieldset(
                    Textarea(
                        listset.text,
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
                action=f"{listset.url}/edit",
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


@rt("/{listset:Entry}/edit")
def post(listset: entries.Entry, title: str, text: str, keywords: list[str] = None):
    "Actually edit the listset."
    assert isinstance(listset, entries.Listset)
    listset.title = (title or "no title").strip()
    listset.text = text.strip()
    listset.keywords = keywords or list()
    listset.write()
    return components.redirect(listset.url)


@rt("/{listset:Entry}/copy")
def get(request, listset: entries.Entry):
    "Form for making a copy of the listset."
    assert isinstance(listset, entries.Listset)
    return (
        Title("Copy"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Copy '{listset.title}'"),
                ),
                cls="listset",
            ),
            cls="container",
        ),
        Main(
            Form(
                Fieldset(
                    Input(
                        type="text",
                        name="title",
                        value=listset.title,
                        placeholder="Title...",
                        required=True,
                        autofocus=True,
                    ),
                ),
                Input(
                    type="submit",
                    value="Save",
                ),
                action=f"{listset.url}/copy",
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
    "Actually copy the listset."
    assert isinstance(source, entries.Listset)
    listset = entries.Listset()
    # XXX For some reason, 'auth' is not set in 'request.scope'?
    listset.owner = session["auth"]
    listset.title = title.strip()
    listset.text = source.text
    listset.keywords = source.keywords
    listset.write()
    return components.redirect(listset.url)


@rt("/{listset:Entry}/delete")
def get(request, listset: entries.Entry):
    "Ask for confirmation to delete the listset."
    assert isinstance(listset, entries.Listset)

    return (
        Title("Delete"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Delete '{listset.title}'"),
                ),
                cls="listset",
            ),
            cls="container",
        ),
        Main(
            P("Really delete the listset? All data will be lost."),
            Form(
                Fieldset(
                    Input(
                        type="submit",
                        value="Yes, delete",
                    ),
                    Input(
                        type="hidden",
                        name="target",
                        value=request.headers["Referer"],
                    ),
                ),
                action=f"{listset.url}/delete",
                method="POST",
            ),
            Form(
                Fieldset(
                    Input(
                        type="submit",
                        value="Cancel",
                        cls="secondary",
                    ),
                ),
                action=request.headers["Referer"],
                method="GET",
            ),
            cls="container",
        ),
    )


@rt("/{listset:Entry}/delete")
def post(listset: entries.Entry, target: str):
    "Actually delete the listset."
    assert isinstance(listset, entries.Listset)
    # XXX Remove from lookup lists in other items.
    listset.delete()
    return components.redirect(target)
