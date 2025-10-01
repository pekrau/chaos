"Link entry pages."

from fasthtml.common import *
import marko

import components
import constants
import entries


app, rt = components.fast_app()


@rt("/")
def get(session):
    "Form for adding a link."
    return (
        Title("Add link"),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
                    Li("Add link"),
                ),
                style=constants.LINK_NAV_STYLE,
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
                    Input(
                        type="href",
                        name="href",
                        placeholder="Href...",
                        required=True,
                    ),
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
                action="/link/",
                method="POST",
            ),
            cls="container",
        ),
    )


@rt("/")
def post(session, title: str, href: str, text: str):
    "Actually add the link."
    link = entries.Link()
    # XXX For some reason, 'auth' is not set in 'request.scope'?
    link.owner = session["auth"]
    link.title = title.strip() or "no title"
    link.href = href.strip() or "/"
    link.content = text.strip()
    link.write()
    entries.set_keywords_relations(link)
    return components.redirect(link.url)


@rt("/{link:Entry}")
def get(session, link: entries.Entry):
    "View the metadata for the link."
    assert isinstance(link, entries.Link)
    return (
        Title(link.title),
        Script(src="/clipboard.min.js"),
        Script("new ClipboardJS('.to_clipboard');"),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
                    Li(
                        components.get_dropdown_menu(
                            A(
                                "Link to clipboard",
                                data_clipboard_action="copy",
                                data_clipboard_text=f"[{link.title}]({link.url})",
                                cls="to_clipboard",
                                href="#",
                            ),
                            A("Edit", href=f"{link.url}/edit"),
                            A("Copy", href=f"{link.url}/copy"),
                            A("Delete", href=f"{link.url}/delete"),
                            A("Add note...", href="/note"),
                            A("Add link...", href="/link"),
                            A("Add file...", href="/file"),
                            A("Keywords", href="/keywords"),
                        ),
                    ),
                    Li(Strong(link.title)),
                    Li(components.search_form()),
                ),
                style=constants.LINK_NAV_STYLE,
            ),
            cls="container",
        ),
        Main(
            Card(
                Strong(A(link.href, href=link.href)),
            ),
            NotStr(marko.convert(link.content)),
            Small(
                Card(
                    Header("Keywords: ", components.get_keywords_links(link)),
                    components.get_entries_table(link.related()),
                ),
            ),
            cls="container",
        ),
        Footer(
            Hr(),
            Div(
                Div(f"{link.size} bytes"),
                Div(link.modified_local),
                cls="grid",
            ),
            cls="container",
        ),
    )


@rt("/{link:Entry}/edit")
def get(session, link: entries.Entry):
    "Form for editing a link."
    assert isinstance(link, entries.Link)
    return (
        Title("Edit"),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
                    Li(f"Edit"),
                    Li(Strong(link.title)),
                ),
                style=constants.LINK_NAV_STYLE,
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
                            value=link.title,
                            required=True,
                        ),
                    ),
                    Label(
                        "Href",
                        Input(
                            type="href",
                            name="href",
                            value=link.href,
                        ),
                    ),
                    Label(
                        "Text",
                        Textarea(
                            link.content,
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
                action=f"{link.url}/edit",
                method="POST",
            ),
            Form(
                Input(
                    type="submit",
                    value="Cancel",
                    cls="secondary",
                ),
                action=link.url,
                method="GET",
            ),
            cls="container",
        ),
    )


@rt("/{link:Entry}/edit")
def post(session, link: entries.Entry, title: str, href: str, text: str):
    "Actually edit the link."
    assert isinstance(link, entries.Link)
    link.title = (title or "no title").strip()
    link.href = href.strip() or "/"
    link.content = text.strip()
    link.write()
    entries.set_keywords_relations(link)
    return components.redirect(link.url)


@rt("/{link:Entry}/copy")
def get(session, link: entries.Entry):
    "Form for making a copy of the link."
    assert isinstance(link, entries.Link)

    return (
        Title("Copy"),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
                    Li("Copy"),
                    Li(Strong(link.title)),
                ),
                style=constants.LINK_NAV_STYLE,
            ),
            cls="container",
        ),
        Main(
            Form(
                Input(
                    type="text",
                    name="title",
                    value=link.title,
                    required=True,
                ),
                Input(
                    type="url",
                    name="href",
                    value=link.href,
                ),
                Textarea(
                    link.content,
                    name="text",
                    rows=10,
                    autofocus=True,
                ),
                Input(
                    type="submit",
                    value="Save",
                ),
                action=f"/link",
                method="POST",
            ),
            Form(
                Input(
                    type="submit",
                    value="Cancel",
                    cls="secondary",
                ),
                action=link.url,
                method="GET",
            ),
            cls="container",
        ),
    )


@rt("/{link:Entry}/delete")
def get(session, link: entries.Entry):
    "Ask for confirmation to delete the link."
    assert isinstance(link, entries.Link)

    return (
        Title("Delete"),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
                    Li("Delete"),
                    Li(Strong(link.title)),
                ),
                style=constants.LINK_NAV_STYLE,
            ),
            cls="container",
        ),
        Main(
            P("Really delete the link? All data will be lost."),
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
                action=f"{link.url}/delete",
                method="POST",
            ),
            cls="container",
        ),
        Footer(
            Hr(),
            Div(
                Div(f"{link.size} bytes"),
                Div(link.modified_local),
                cls="grid",
            ),
            cls="container",
        ),
    )


@rt("/{link:Entry}/delete")
def post(session, link: entries.Entry, action: str):
    "Actually delete the link."
    assert isinstance(link, entries.Link)
    if "yes" in action.casefold():
        link.delete()
        return components.redirect(f"/")
    else:
        return components.redirect(link.url)
