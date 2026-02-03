"Listset (ordered set) item pages."

from fasthtml.common import *
import marko

import components
import constants
import items


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
                    Details(
                        Summary("Add to listsets..."),
                        Ul(*components.get_listsets_dropdown(None)),
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
                    type="text",
                    name="add",
                    placeholder="Identifiers for items to add...",
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
def post(session, title: str, text: str, keywords: list[str] = None, listsets: list[str] = None, add: str = ""):
    "Actually add the listset."
    listset = items.Listset()
    # XXX For some reason, 'auth' is not set in 'request.scope'?
    listset.owner = session["auth"]
    listset.title = title.strip() or "no title"
    listset.text = text.strip()
    listset.keywords = keywords or list()
    for id in (listsets or list()):
        other = items.get(id)
        assert isinstance(other, items.Listset)
        other.add(listset)
        other.write()
    listset.frontmatter["items"] = list()
    for id in add.replace(",", " ").split():
        try:
            item = items.get(id)
        except KeyError:
            pass
        else:
            try:
                listset.add(item)
            except ValueError:
                pass
    listset.write()
    return components.redirect(listset.url)


@rt("/{listset:Item}")
def get(listset: items.Item):
    "View the listset."
    assert isinstance(listset, items.Listset)
    return (
        Title(listset.title),
        Script(src="/clipboard.min.js"),
        Script("new ClipboardJS('.to_clipboard');"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(Strong(listset.title)),
                    Li(*components.get_item_links(listset)),
                ),
                Ul(Li(components.search_form())),
                cls="listset",
            ),
            cls="container",
        ),
        Main(
            Card(NotStr(marko.convert(listset.text))),
            Card(components.get_items_table(listset.items)),
            components.get_listsets_card(listset),
            components.get_keywords_items_card(listset),
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


@rt("/{listset:Item}/edit")
def get(request, listset: items.Item):
    "Form for editing a listset."
    assert isinstance(listset, items.Listset)
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
                Div(
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
                    Details(
                        Summary("Add to listsets..."),
                        Ul(*components.get_listsets_dropdown(listset)),
                        cls="dropdown",
                    ),
                    cls="grid",
                ),
                Textarea(
                    listset.text,
                    name="text",
                    rows=10,
                    placeholder="Text...",
                    autofocus=True,
                ),
                components.get_items_table(listset.items, edit=True),
                Input(
                    type="text",
                    name="add",
                    placeholder="Identifiers for items to add...",
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


@rt("/{listset:Item}/edit")
def post(
    listset: items.Item,
    title: str,
    text: str,
    form: dict,
    keywords: list[str] = None,
    listsets: list[str] = None,
    add: str = "",
    remove: list[str] = None,
):
    "Actually edit the listset."
    assert isinstance(listset, items.Listset)
    listset.title = (title or "no title").strip()
    listset.text = text.strip()
    listset.keywords = keywords or list()
    for id in (listsets or list()):
        other = items.get(id)
        assert isinstance(other, items.Listset)
        other.add(listset)
        other.write()
    # First remove items.
    for id in remove:
        listset.remove(id)
    # Next, change position of remaining items.
    positions = [
        (int(form[f"position_{id}"]), id) for id in listset.frontmatter["items"]
    ]
    positions.sort(key=lambda t: t[0])
    listset.frontmatter["items"] = [t[1] for t in positions]
    # Lastly, add new items.
    for id in add.replace(",", " ").split():
        try:
            item = items.get(id)
        except KeyError:
            pass
        else:
            try:
                listset.add(item)
            except ValueError:
                pass
    listset.write()
    return components.redirect(listset.url)


@rt("/{listset:Item}/copy")
def get(request, listset: items.Item):
    "Form for making a copy of the listset."
    assert isinstance(listset, items.Listset)
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
                Input(
                    type="text",
                    name="title",
                    value=listset.title,
                    placeholder="Title...",
                    required=True,
                    autofocus=True,
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


@rt("/{source:Item}/copy")
def post(session, source: items.File, title: str):
    "Actually copy the listset."
    assert isinstance(source, items.Listset)
    listset = items.Listset()
    # XXX For some reason, 'auth' is not set in 'request.scope'?
    listset.owner = session["auth"]
    listset.title = title.strip()
    listset.text = source.text
    listset.keywords = source.keywords
    listset.frontmatter["items"] = list(source.frontmatter["items"])
    listset.write()
    return components.redirect(listset.url)


@rt("/{listset:Item}/delete")
def get(request, listset: items.Item):
    "Ask for confirmation to delete the listset."
    assert isinstance(listset, items.Listset)

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
                Input(
                    type="submit",
                    value="Yes, delete",
                ),
                Input(
                    type="hidden",
                    name="target",
                    value=request.headers["Referer"],
                ),
                action=f"{listset.url}/delete",
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


@rt("/{listset:Item}/delete")
def post(listset: items.Item, target: str):
    "Actually delete the listset."
    assert isinstance(listset, items.Listset)
    # XXX Remove from lookup lists in other items.
    listset.delete()
    return components.redirect(target)
