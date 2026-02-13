"Graphic item pages."

import json
import urllib.parse

from fasthtml.common import *

import components
import constants
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
                Div(
                    Input(
                        type="text",
                        name="title",
                        placeholder="Title...",
                        required=True,
                        autofocus=True,
                    ),
                    Details(
                        Summary("Add to listsets..."),
                        Ul(*components.get_listsets_dropdown(None)),
                        cls="dropdown",
                    ),
                    Details(
                        Summary("Keywords..."),
                        Ul(*components.get_keywords_dropdown(keywords=list())),
                        cls="dropdown",
                    ),
                    cls="grid",
                ),
                Textarea(
                    name="text",
                    rows=10,
                    placeholder="Text...",
                ),
                Select(
                    Option(
                        "Select graphic format", selected=True, disabled=True, value=""
                    ),
                    *[Option(f) for f in constants.GRAPHIC_FORMATS],
                    name="format",
                ),
                Textarea(
                    name="specification",
                    rows=10,
                    placeholder="Specification...",
                    cls="specification",
                ),
                Input(
                    type="submit",
                    value="Save",
                ),
                action="/graphic/",
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
def post(
    session,
    title: str,
    text: str,
    format: str,
    specification: str,
    listsets: list[str] = None,
    keywords: list[str] = None,
):
    "Actually add the graphic."
    graphic = items.Graphic()
    # XXX For some reason, 'auth' is not set in 'request.scope'?
    graphic.owner = session["auth"]
    graphic.title = title.strip() or "no title"
    graphic.text = text.strip()
    if format == constants.VEGA_LITE:
        graphic.frontmatter["format"] = format
        try:
            graphic.frontmatter["specification"] = json.dumps(
                json.loads(specification.strip()), indent=2, ensure_ascii=False
            )
        except json.decoder.JSONDecodeError as error:
            errors.Error(str(error))
    else:
        errors.Error("unknown graphics format.")
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
        # Script(src="https://cdn.jsdelivr.net/npm/vega@5.25"),
        # Script(src="https://cdn.jsdelivr.net/npm/vega-lite@5.12"),
        # Script(src="https://cdn.jsdelivr.net/npm/vega-embed@6.22"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(components.get_graphic_icon(), Strong(graphic.title)),
                    Li(*components.get_item_links(graphic)),
                ),
                Ul(Li(components.search_form())),
            ),
            cls="container",
        ),
        Main(
            Div(id="graphic"),
            components.get_text_card(graphic),
            components.get_listsets_card(graphic),
            components.get_keywords_card(graphic),
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
        Title("Edit"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Edit '{graphic.title}'"),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                Div(
                    Input(
                        type="text",
                        name="title",
                        value=graphic.title,
                        placeholder="Title...",
                        required=True,
                    ),
                    Details(
                        Summary("Add to listsets..."),
                        Ul(*components.get_listsets_dropdown(graphic)),
                        cls="dropdown",
                    ),
                    Details(
                        Summary("Keywords..."),
                        Ul(*components.get_keywords_dropdown(graphic.keywords)),
                        cls="dropdown",
                    ),
                    cls="grid",
                ),
                Textarea(
                    graphic.text,
                    name="text",
                    rows=10,
                    placeholder="Text...",
                    autofocus=True,
                ),
                Input(
                    type="text",
                    name="format",
                    value=graphic.format,
                    disabled=True,
                ),
                Textarea(
                    graphic.specification,
                    name="specification",
                    rows=10,
                    cls="specification",
                ),
                Input(
                    type="submit",
                    value="Save",
                ),
                action=f"{graphic.url}/edit",
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
    if graphic.format == constants.VEGA_LITE:
        try:
            graphic.frontmatter["specification"] = json.dumps(
                json.loads(specification.strip()), indent=2, ensure_ascii=False
            )
        except json.decoder.JSONDecodeError as error:
            errors.Error(str(error))
    else:
        errors.Error("unknown graphics format.")
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
                    value="Copy",
                ),
                action=f"{graphic.url}/copy",
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
    "Actually copy the graphic."
    assert isinstance(source, items.Graphic)
    graphic = items.Graphic()
    # XXX For some reason, 'auth' is not set in 'request.scope'?
    graphic.owner = session["auth"]
    graphic.title = title.strip()
    graphic.text = source.text
    graphic.frontmatter["format"] = source.format
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
        Title("Delete"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Delete '{graphic.title}'"),
                ),
            ),
            cls="container",
        ),
        Main(
            P("Really delete the graphic? All data will be lost."),
            Form(
                Input(
                    type="submit",
                    value="Yes, delete",
                ),
                Input(
                    type="hidden",
                    name="redirect",
                    value=redirect,
                ),
                action=f"{graphic.url}/delete",
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


@rt("/{graphic:Item}/delete")
def post(graphic: items.Item, redirect: str):
    "Actually delete the graphic."
    assert isinstance(graphic, items.Graphic)
    graphic.delete()
    return components.redirect(redirect)
