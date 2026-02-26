"Listset (ordered set) item pages."

import urllib.parse

from fasthtml.common import *

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
                    Li(components.get_listset_icon(), "Add listset"),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                components.get_title_input(None),
                Input(
                    type="text",
                    name="add",
                    placeholder="Identifiers for items to add...",
                ),
                components.get_text_input(None),
                components.get_listset_keyword_inputs(None),
                Input(type="submit", value="Add listset"),
                action="/listset/",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/")
def post(
    request,
    title: str,
    text: str,
    listsets: list[str] = None,
    keywords: list[str] = None,
    add: str = "",
):
    "Actually add the listset."
    listset = items.Listset()
    listset.owner = request.scope["auth"]
    listset.title = title.strip() or "no title"
    listset.text = text.strip()
    for id in listsets or list():
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
    listset.keywords = keywords or list()
    listset.write()
    return components.redirect(listset.url)


@rt("/{listset:Item}")
def get(listset: items.Item):
    "View the listset."
    assert isinstance(listset, items.Listset)
    return (
        Title(listset.title),
        Script(src="/clipboard.min.js"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(components.get_listset_icon(), listset.title),
                    Li(*components.get_item_links(listset)),
                ),
                Ul(Li(components.search_form())),
            ),
            cls="container",
        ),
        Main(
            components.get_text_card(listset),
            Card(components.get_items_table(listset.items)),
            Div(
                components.get_listsets_card(listset),
                components.get_keywords_card(listset),
                cls="grid",
            ),
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
        Script("new ClipboardJS('.to_clipboard');", type="text/javascript"),
    )


@rt("/{listset:Item}/edit")
def get(request, listset: items.Item):
    "Form for editing a listset."
    assert isinstance(listset, items.Listset)
    return (
        Title(f"Edit {listset.title}"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(Strong("Edit "), listset.title),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                components.get_title_input(listset),
                components.get_items_table(listset.items, edit=True),
                Input(
                    type="text",
                    name="add",
                    placeholder="Identifiers for items to add...",
                ),
                components.get_text_input(listset),
                components.get_listset_keyword_inputs(listset),
                Input(type="submit", value="Save"),
                action=f"{listset.url}/edit",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/{listset:Item}/edit")
def post(
    listset: items.Item,
    title: str,
    text: str,
    form: dict,
    listsets: list[str] = None,
    add: str = "",
    remove: list[str] = None,
    keywords: list[str] = None,
):
    "Actually edit the listset."
    assert isinstance(listset, items.Listset)
    listset.title = (title or "no title").strip()
    listset.text = text.strip()
    for id in listsets or list():
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
    listset.keywords = keywords or list()
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
                Input(type="submit", value="Copy listset"),
                action=f"{listset.url}/copy",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/{source:Item}/copy")
def post(request, source: items.File, title: str):
    "Actually copy the listset."
    assert isinstance(source, items.Listset)
    listset = items.Listset()
    listset.owner = request.scope["auth"]
    listset.title = title.strip()
    listset.text = source.text
    listset.frontmatter["items"] = list(source.frontmatter["items"])
    listset.keywords = source.keywords
    listset.write()
    return components.redirect(listset.url)


@rt("/{listset:Item}/delete")
def get(request, listset: items.Item):
    "Ask for confirmation to delete the listset."
    assert isinstance(listset, items.Listset)
    redirect = urllib.parse.urlsplit(request.headers["Referer"]).path
    if redirect == f"/listset/{listset.id}":
        redirect = "/listsets"
    return (
        Title(f"Delete {listset.title}"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(Strong("Delete "), listset.title),
                ),
            ),
            cls="container",
        ),
        Main(
            H3("Really delete the listset? All data will be lost."),
            Form(
                Input(type="hidden", name="redirect", value=redirect),
                Input(type="submit", value="Yes, delete"),
                action=f"{listset.url}/delete",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/{listset:Item}/delete")
def post(listset: items.Item, redirect: str):
    "Actually delete the listset."
    assert isinstance(listset, items.Listset)
    listset.delete()
    return components.redirect(redirect)
