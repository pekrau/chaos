"Image item pages."

from http import HTTPStatus as HTTP
import mimetypes
import pathlib
import urllib.parse


from fasthtml.common import *

import components
import constants
import items
import settings


app, rt = components.get_app_rt()


@rt("/")
def get(request):
    "Form for adding an image."
    return (
        Title("Add image"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li("Add image"),
                ),
                cls="image",
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
                Div(
                    Input(
                        type="file",
                        name="upfile",
                        placeholder="image...",
                        required=True,
                        accept=",".join(constants.IMAGE_MIMETYPES),
                    ),
                    cls="grid",
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
                action="/image/",
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
async def post(
    session,
    title: str,
    upfile: UploadFile,
    text: str,
    listsets: list[str] = None,
    keywords: list[str] = None,
):
    "Actually add the image."
    filename = pathlib.Path(upfile.filename)
    if upfile.content_type not in constants.IMAGE_MIMETYPES:
        raise components.Error("Cannot upload non-image file.")
    ext = filename.suffix
    if ext == ".md":
        raise components.Error("Upload of Markdown file is disallowed.")
    image = items.Image()
    # XXX For some reason, 'auth' is not set in 'request.scope'?
    image.owner = session["auth"]
    image.title = title.strip() or filename.stem
    filecontent = await upfile.read()
    filename = image.id + ext
    image.frontmatter["filename"] = filename
    try:
        with open(f"{constants.DATA_DIR}/{filename}", "wb") as outfile:
            outfile.write(filecontent)
    except OSError as error:
        raise components.Error(error)
    image.text = text.strip()
    for id in listsets or list():
        listset = items.get(id)
        assert isinstance(listset, items.Listset)
        listset.add(image)
        listset.write()
    image.keywords = keywords or list()
    image.write()
    return components.redirect(image.url)


@rt("/{image:Item}")
def get(image: items.Item):
    "View the metadata for the image."
    assert isinstance(image, items.Image)
    return (
        Title(image.title),
        Script(src="/clipboard.min.js"),
        Script("new ClipboardJS('.to_clipboard');"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(components.get_image_icon(), Strong(image.title)),
                    Li(*components.get_item_links(image)),
                ),
                Ul(Li(components.search_form())),
                cls="image",
            ),
            cls="container",
        ),
        Main(
            Card(
                A(
                    Img(src=image.bin_url, title=image.filename, cls="display"),
                    href=image.bin_url,
                )
            ),
            components.get_text_card(image),
            components.get_listsets_card(image),
            components.get_keywords_card(image),
            cls="container",
        ),
        Footer(
            Hr(),
            Div(
                Div(image.modified_local),
                Div(f"{image.size:,d} + {image.file_size:,d} bytes"),
                Div(image.owner),
                cls="grid",
            ),
            cls="container",
        ),
    )


@rt("/{image:Item}/edit")
def get(request, image: items.Item):
    "Form for editing metadata for the image."
    assert isinstance(image, items.Image)
    return (
        Title("Edit"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Edit '{image.title}'"),
                ),
                cls="image",
            ),
            cls="container",
        ),
        Main(
            Form(
                Div(
                    Input(
                        type="text",
                        name="title",
                        value=image.title,
                        required=True,
                        placeholder="Title...",
                    ),
                    Details(
                        Summary("Add to listsets..."),
                        Ul(*components.get_listsets_dropdown(image)),
                        cls="dropdown",
                    ),
                    Details(
                        Summary("Keywords..."),
                        Ul(*components.get_keywords_dropdown(image.keywords)),
                        cls="dropdown",
                    ),
                    cls="grid",
                ),
                Div(
                    Div(
                        Input(
                            type="file",
                            name="upfile",
                        ),
                        Img(
                            src=image.bin_url,
                            title=image.filename,
                            cls="display",
                        ),
                    ),
                    cls="grid",
                ),
                Textarea(
                    image.text,
                    name="text",
                    rows=10,
                    placeholder="Text...",
                    autofocus=True,
                ),
                Input(
                    type="submit",
                    value="Save",
                ),
                action=f"{image.url}/edit",
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


@rt("/{image:Item}/edit")
async def post(
    image: items.Item,
    title: str,
    upfile: UploadFile,
    text: str,
    listsets: list[str] = None,
    keywords: list[str] = None,
):
    "Actually edit the image."
    assert isinstance(image, items.Image)
    image.title = title.strip() or image.filename.stem
    if upfile.filename:
        ext = pathlib.Path(upfile.filename).suffix
        if ext == ".md":
            raise components.Error("Upload of Markdown file is disallowed.")
        filecontent = await upfile.read()
        filename = image.id + ext  # The mimetype may change on file contents update.
        try:
            with open(f"{constants.DATA_DIR}/{filename}", "wb") as outfile:
                outfile.write(filecontent)
        except OSError as error:
            raise components.Error(error)
    image.text = text.strip()
    for id in listsets or list():
        listset = items.get(id)
        assert isinstance(listset, items.Listset)
        listset.add(image)
        listset.write()
    image.keywords = keywords or list()
    image.write()
    return components.redirect(image.url)


@rt("/{image:Item}/copy")
def get(request, image: items.Item):
    "Form for making a copy of the image."
    assert isinstance(image, items.Image)
    return (
        Title("Copy"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Copy '{image.title}'"),
                ),
                cls="image",
            ),
            cls="container",
        ),
        Main(
            Form(
                Input(
                    type="text",
                    name="title",
                    value=image.title,
                    placeholder="Title...",
                    required=True,
                    autofocus=True,
                ),
                Input(
                    type="submit",
                    value="Copy",
                ),
                action=f"{image.url}/copy",
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
    "Actually copy the image."
    assert isinstance(source, items.Image)
    filename = pathlib.Path(source.filename)
    image = items.Image()
    # XXX For some reason, 'auth' is not set in 'request.scope'?
    image.owner = session["auth"]
    image.title = title.strip()
    image.text = source.text
    with open(source.filepath, "rb") as infile:
        filecontent = infile.read()
    filename = image.id + filename.suffix
    try:
        with open(f"{constants.DATA_DIR}/{filename}", "wb") as outfile:
            outfile.write(filecontent)
    except OSError as error:
        raise components.Error(error)
    image.frontmatter["filename"] = filename
    image.keywords = source.keywords
    image.write()
    return components.redirect(image.url)


@rt("/{image:Item}/delete")
def get(request, image: items.Item):
    "Ask for confirmation to delete the file image."
    assert isinstance(image, items.Image)
    target = urllib.parse.urlsplit(request.headers["Referer"]).path
    if target == f"/image/{image.id}":
        target = "/images"
    return (
        Title("Delete"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Delete '{image.title}'"),
                ),
                cls="image",
            ),
            cls="container",
        ),
        Main(
            P("Really delete the image? All data will be lost."),
            Form(
                Input(
                    type="submit",
                    value="Yes, delete",
                ),
                Input(
                    type="hidden",
                    name="target",
                    value=target,
                ),
                action=f"{image.url}/delete",
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


@rt("/{image:Item}/delete")
def post(image: items.Item, target: str):
    "Actually delete the image."
    assert isinstance(image, items.Image)
    image.delete()
    return components.redirect(target)
