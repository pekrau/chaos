"Graphic item pages."

import json
import urllib.parse

from fasthtml.common import *
import requests

import components
import constants
import errors
import items
import minixml

app, rt = components.get_app_rt()


@rt("/")
def get():
    "Form for adding a graphic."
    title = "Add graphic"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(title),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                components.get_title_input(),
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
                components.get_text_input(),
                components.get_tags_input(),
                Input(type="submit", value="Add graphic"),
                action="/graphic/",
                method="POST",
            ),
            components.get_cancel_form("/"),
            cls="container",
        ),
    )


@rt("/")
def post(
    title: str, text: str, graphic_type: str, specification: str, tags: list[str] = None
):
    "Actually add the graphic."
    graphic = items.Graphic()
    graphic.title = title.strip() or "no title"

    match graphic_type:

        case constants.VEGA_LITE:
            try:
                specification = json.dumps(
                    json.loads(specification.strip()), indent=2, ensure_ascii=False
                )
            except json.decoder.JSONDecodeError as error:
                raise errors.Error(str(error))

        case constants.SVG:
            try:
                xml = minixml.parse(specification.strip())
                xml.repr_indent = None
                specification = repr(xml)
            except ValueError as error:
                raise errors.Error(str(error))

        case _:
            raise errors.Error("unknown graphic type.")

    graphic.frontmatter["graphic"] = graphic_type
    graphic.frontmatter["specification"] = specification
    graphic.text = text.strip()
    graphic.tags = tags
    graphic.write()
    return components.redirect(graphic.url)


@rt("/{graphic:Item}")
def get(graphic: items.Item, page: int = 1, tags_page: int = 1, refs_page: int = 1):
    "View the graphic."
    assert isinstance(graphic, items.Graphic)

    match graphic.frontmatter["graphic"]:

        case constants.VEGA_LITE:
            header_scripts = [
                Script(src="https://cdn.jsdelivr.net/npm/vega@6"),
                Script(src="https://cdn.jsdelivr.net/npm/vega-lite@6"),
                Script(src="https://cdn.jsdelivr.net/npm/vega-embed@7"),
            ]
            display = Div(id="graphic")
            footer_scripts = [
                Script(
                    f"""const specification = {graphic.specification};
vegaEmbed("#graphic", specification, {{downloadFileName: "filename"}})
.then(result=>console.log(result))
.catch(console.warn);
""",
                    type="text/javascript",
                ),
            ]

        case constants.SVG:
            header_scripts = []
            display = NotStr(graphic.specification)
            footer_scripts = []

        case _:
            raise NotImplementedError

    return (
        Title(graphic.title),
        components.clipboard_script(),
        *header_scripts,
        components.get_header_item_view(graphic),
        Main(
            Card(
                display,
                Footer(graphic.frontmatter["graphic"]),
            ),
            components.get_text_card(graphic),
            Form(
                components.get_tags_card(graphic, tags_page),
                components.get_refs_card(graphic, refs_page),
                action=graphic.url,
            ),
            cls="container",
        ),
        components.get_footer_item_view(graphic),
        components.clipboard_activate(),
        *footer_scripts,
    )


@rt("/{graphic:Item}/edit")
def get(request, graphic: items.Item):
    "Form for editing a graphic."
    assert isinstance(graphic, items.Graphic)

    # Make the specification presentable.
    match graphic.frontmatter["graphic"]:

        case constants.VEGA_LITE:
            specification = json.dumps(
                json.loads(graphic.specification),
                indent=2,
                ensure_ascii=False,
            )

        case constants.SVG:
            specification = repr(minixml.parse(graphic.specification))

        case _:
            raise NotImplementedError

    return (
        *components.get_header_item_edit(graphic),
        Main(
            Form(
                components.get_title_input(graphic.title),
                Input(
                    type="text",
                    name="graphic",
                    value=graphic.graphic,
                    disabled=True,
                ),
                Textarea(
                    specification,
                    name="specification",
                    rows=10,
                    cls="specification",
                ),
                components.get_text_input(graphic.text),
                components.get_tags_input(graphic.tags),
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
    tags: list[str] = None,
):
    "Actually edit the graphic."
    assert isinstance(graphic, items.Graphic)

    match graphic.graphic:

        case constants.VEGA_LITE:
            try:
                specification = json.dumps(
                    json.loads(specification.strip()), ensure_ascii=False
                )
            except json.decoder.JSONDecodeError as error:
                raise errors.Error(str(error))

        case constants.SVG:
            try:
                xml = minixml.parse(specification.strip())
                xml.repr_indent = None
                specification = repr(xml)
            except ValueError as error:
                raise errors.Error(str(error))

        case _:
            raise errors.Error("unknown graphic type.")

    graphic.frontmatter["specification"] = specification
    graphic.title = title.strip()
    graphic.text = text.strip()
    graphic.tags = tags
    graphic.write()
    return components.redirect(graphic.url)


@rt("/{graphic:Item}/copy")
def get(request, graphic: items.Item):
    "Form for making a copy of the graphic."
    assert isinstance(graphic, items.Graphic)
    title = f"Copy '{graphic.title}'"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(graphic)),
                    Li(title),
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
                ),
                Input(type="submit", value="Copy graphic"),
                action=f"{graphic.url}/copy",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/{source:Item}/copy")
def post(source: items.File, title: str):
    "Actually copy the graphic."
    assert isinstance(source, items.Graphic)
    graphic = items.Graphic()
    graphic.title = title.strip()
    graphic.text = source.text
    graphic.frontmatter["graphic"] = source.graphic
    graphic.frontmatter["specification"] = source.specification
    graphic.write()
    return components.redirect(graphic.url)


@rt("/{graphic:Item}/delete")
def get(request, graphic: items.Item):
    "Ask for confirmation to delete the graphic."
    assert isinstance(graphic, items.Graphic)
    redirect = urllib.parse.urlsplit(request.headers["Referer"]).path
    if redirect == f"/graphic/{graphic.id}":
        redirect = "/"
    title = f"Delete '{graphic.title}'"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(graphic)),
                    Li(title),
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
                Input(type="submit", value="Yes, delete"),
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
