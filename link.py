"Link entry pages."

from fasthtml.common import *
import marko

import components
import constants
import entries


app, rt = components.get_app_rt()


@rt("/")
def get(request):
    "Form for adding a link."
    return (
        Title("Add link"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li("Add link"),
                ),
                cls="link",
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
                    Input(
                        type="href",
                        name="href",
                        placeholder="Href...",
                        required=True,
                    ),
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
                action="/link/",
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
def post(session, title: str, href: str, text: str, keywords: list[str] = []):
    "Actually add the link."
    link = entries.Link()
    # XXX For some reason, 'auth' is not set in 'request.scope'?
    link.owner = session["auth"]
    link.title = title.strip() or "no title"
    link.href = href.strip() or "/"
    link.text = text.strip()
    link.keywords = keywords
    link.write()
    return components.redirect(link.url)


@rt("/{link:Entry}")
def get(link: entries.Entry):
    "View the metadata for the link."
    assert isinstance(link, entries.Link)
    return (
        Title(link.title),
        Script(src="/clipboard.min.js"),
        Script("new ClipboardJS('.to_clipboard');"),
        Header(
            Nav(
                Ul(
                    Li(
                        components.get_nav_menu(
                            A(Strong("Edit"), href=f"{link.url}/edit"),
                            A(Strong("Copy"), href=f"{link.url}/copy"),
                            A(Strong("Delete"), href=f"{link.url}/delete"),
                        )
                    ),
                    Li(components.get_entry_clipboard(link), link.title),
                    Li(components.search_form()),
                ),
                cls="link",
            ),
            cls="container",
        ),
        Main(
            Card(
                Strong(A(link.href, href=link.href)),
            ),
            NotStr(marko.convert(link.text)),
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
                Div(link.modified_local),
                Div(f"{link.size} bytes"),
                Div(link.owner),
                cls="grid",
            ),
            cls="container",
        ),
    )


@rt("/{link:Entry}/edit")
def get(link: entries.Entry):
    "Form for editing a link."
    assert isinstance(link, entries.Link)
    return (
        Title("Edit"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Edit '{link.title}'"),
                ),
                cls="link",
            ),
            cls="container",
        ),
        Main(
            Form(
                Fieldset(
                    Input(
                        type="text",
                        name="title",
                        value=link.title,
                        placeholder="Title...",
                        required=True,
                    ),
                    Details(
                        Summary("Keywords..."),
                        Ul(*components.get_keywords_dropdown(link.keywords)),
                        cls="dropdown",
                    ),
                    cls="grid",
                ),
                Fieldset(
                    Input(
                        type="href",
                        name="href",
                        value=link.href,
                        placeholder="Href...",
                        required=True,
                    ),
                ),
                Fieldset(
                    Textarea(
                        link.text,
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
def post(link: entries.Entry, title: str, href: str, text: str, keywords: list[str] = []):
    "Actually edit the link."
    assert isinstance(link, entries.Link)
    link.title = (title or "no title").strip()
    link.href = href.strip() or "/"
    link.text = text.strip()
    link.keywords = keywords
    link.write()
    return components.redirect(link.url)


@rt("/{link:Entry}/copy")
def get(link: entries.Entry):
    "Form for making a copy of the link."
    assert isinstance(link, entries.Link)
    return (
        Title("Copy"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Copy '{link.title}'"),
                ),
                cls="link",
            ),
            cls="container",
        ),
        Main(
            Form(
                Fieldset(
                    Input(
                        type="text",
                        name="title",
                        value=link.title,
                        placeholder="Title...",
                        required=True,
                        autofocus=True,
                    ),
                ),
                Input(
                    type="submit",
                    value="Save",
                ),
                action=f"/link/{link}/copy",
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


@rt("/{source:Entry}/copy")
def post(session, source: entries.File, title: str):
    "Actually copy the link."
    assert isinstance(source, entries.Link)
    link = entries.Link()
    # XXX For some reason, 'auth' is not set in 'request.scope'?
    link.owner = session["auth"]
    link.title = title.strip()
    link.href = source.href
    link.text = source.text
    link.keywords = source.keywords
    link.write()
    return components.redirect(link.url)


@rt("/{link:Entry}/delete")
def get(link: entries.Entry):
    "Ask for confirmation to delete the link."
    assert isinstance(link, entries.Link)

    return (
        Title("Delete"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Delete '{link.title}'"),
                ),
                cls="link",
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
    )


@rt("/{link:Entry}/delete")
def post(link: entries.Entry, action: str):
    "Actually delete the link."
    assert isinstance(link, entries.Link)
    if "yes" in action.casefold():
        link.delete()
        return components.redirect(f"/")
    else:
        return components.redirect(link.url)
