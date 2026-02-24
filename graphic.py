"Graphic item pages."

import json
import urllib.parse

from fasthtml.common import *
import requests

import components
import constants
import errors
import items
import settings

app, rt = components.get_app_rt()


@rt("/")
def get(request):
    "Form for adding a graphic."
    return (
        Title("Add graphic"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(components.get_graphic_icon(), "Add graphic"),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                components.get_title_input(None),
                Select(
                    Option(
                        "Select graphic type", selected=True, disabled=True, value=""
                    ),
                    *[Option(f) for f in constants.GRAPHIC_TYPES],
                    name="graphic_type",
                ),
                Textarea(
                    name="specification",
                    rows=10,
                    placeholder="Specification...",
                    cls="specification",
                ),
                components.get_text_input(None),
                components.get_listset_keyword_inputs(None),
                Input(type="submit", value="Add graphic"),
                action="/graphic/",
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
    graphic_type: str,
    specification: str,
    listsets: list[str] = None,
    keywords: list[str] = None,
):
    "Actually add the graphic."
    graphic = items.Graphic()
    graphic.owner = request.scope["auth"]
    graphic.title = title.strip() or "no title"
    graphic.text = text.strip()
    if graphic_type == constants.VEGA_LITE:
        graphic.frontmatter["graphic"] = graphic_type
        try:
            graphic.frontmatter["specification"] = json.dumps(
                json.loads(specification.strip()), indent=2, ensure_ascii=False
            )
        except json.decoder.JSONDecodeError as error:
            errors.Error(str(error))
    else:
        errors.Error("unknown graphic type.")
    for id in listsets or list():
        listset = items.get(id)
        assert isinstance(listset, items.Listset)
        listset.add(graphic)
        listset.write()
    graphic.keywords = keywords or list()
    graphic.write()
    return components.redirect(graphic.url)


@rt("/{graphic:Item}")
def get(graphic: items.Item):
    "View the graphic."
    assert isinstance(graphic, items.Graphic)
    return (
        Title(graphic.title),
        Script(src="/clipboard.min.js"),
        Script(src="https://cdn.jsdelivr.net/npm/vega@6"),
        Script(src="https://cdn.jsdelivr.net/npm/vega-lite@6"),
        Script(src="https://cdn.jsdelivr.net/npm/vega-embed@7"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(components.get_graphic_icon(), graphic.title),
                    Li(*components.get_item_links(graphic)),
                ),
                Ul(Li(components.search_form())),
            ),
            cls="container",
        ),
        Main(
            Div(id="graphic"),
            components.get_text_card(graphic),
            Div(
                components.get_listsets_card(graphic),
                components.get_keywords_card(graphic),
                cls="grid",
            ),
            cls="container",
        ),
        Footer(
            Hr(),
            Div(
                Div(graphic.modified_local),
                Div(f"{graphic.size} bytes"),
                Div(graphic.owner),
                cls="grid",
            ),
            cls="container",
        ),
        Script("new ClipboardJS('.to_clipboard');", type="text/javascript"),
        Script(
            f"""
const specification = {graphic.specification};
vegaEmbed("#graphic", specification, {{downloadFileName: "filename"}})
.then(result=>console.log(result))
.catch(console.warn);
""",
            type="text/javascript",
        ),
    )


@rt("/{graphic:Item}/edit")
def get(request, graphic: items.Item):
    "Form for editing a graphic."
    assert isinstance(graphic, items.Graphic)
    return (
        Title(f"Edit {database.title}"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(Strong("Edit "), graphic.title),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                components.get_title_input(graphic),
                Input(
                    type="text",
                    name="graphic",
                    value=graphic.graphic,
                    disabled=True,
                ),
                Textarea(
                    graphic.specification,
                    name="specification",
                    rows=10,
                    cls="specification",
                ),
                components.get_text_input(graphic),
                components.get_listset_keyword_inputs(graphic),
                Input(type="submit", value="Save"),
                action=f"{graphic.url}/edit",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/{graphic:Item}/edit")
def post(
    graphic: items.Item,
    title: str,
    text: str,
    specification: str,
    listsets: list[str] = None,
    keywords: list[str] = None,
):
    "Actually edit the graphic."
    assert isinstance(graphic, items.Graphic)
    graphic.title = title or "no title"
    graphic.text = text.strip()
    if graphic.graphic == constants.VEGA_LITE:
        try:
            graphic.frontmatter["specification"] = json.dumps(
                json.loads(specification.strip()), indent=2, ensure_ascii=False
            )
        except json.decoder.JSONDecodeError as error:
            errors.Error(str(error))
    else:
        errors.Error("unknown graphic type.")
    for id in listsets or list():
        listset = items.get(id)
        assert isinstance(listset, items.Listset)
        listset.add(graphic)
        listset.write()
    graphic.keywords = keywords or list()
    graphic.write()
    return components.redirect(graphic.url)


@rt("/{graphic:Item}/copy")
def get(request, graphic: items.Item):
    "Form for making a copy of the graphic."
    assert isinstance(graphic, items.Graphic)
    return (
        Title("Copy"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Copy '{graphic.title}'"),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                Input(
                    type="text",
                    name="title",
                    value=graphic.title,
                    placeholder="Title...",
                    required=True,
                    autofocus=True,
                ),
                Input(
                    type="submit",
                    value="Copy graphic",
                ),
                action=f"{graphic.url}/copy",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/{source:Item}/copy")
def post(request, source: items.File, title: str):
    "Actually copy the graphic."
    assert isinstance(source, items.Graphic)
    graphic = items.Graphic()
    graphic.owner = request.scope["auth"]
    graphic.title = title.strip()
    graphic.text = source.text
    graphic.frontmatter["graphic"] = source.graphic
    graphic.frontmatter["specification"] = source.specification
    graphic.keywords = source.keywords
    graphic.write()
    return components.redirect(graphic.url)


@rt("/{graphic:Item}/delete")
def get(request, graphic: items.Item):
    "Ask for confirmation to delete the graphic."
    assert isinstance(graphic, items.Graphic)
    redirect = urllib.parse.urlsplit(request.headers["Referer"]).path
    if redirect == f"/graphic/{graphic.id}":
        redirect = "/graphics"
    return (
        Title(f"Delete {graphic.title}"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(Strong("Delete "), graphic.title),
                ),
            ),
            cls="container",
        ),
        Main(
            H3("Really delete the graphic? All data will be lost."),
            Form(
                Input(
                    type="hidden",
                    name="redirect",
                    value=redirect,
                ),
                Input(
                    type="submit",
                    value="Yes, delete",
                ),
                action=f"{graphic.url}/delete",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/{graphic:Item}/delete")
def post(graphic: items.Item, redirect: str):
    "Actually delete the graphic."
    assert isinstance(graphic, items.Graphic)
    graphic.delete()
    return components.redirect(redirect)
