"Image item pages."

from http import HTTPStatus as HTTP
import mimetypes
import pathlib
import urllib.parse


from fasthtml.common import *

import components
import constants
import errors
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
                    Li(components.get_image_icon(), "Add image"),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                components.get_title_input(None),
                Input(
                    type="file",
                    name="upfile",
                    required=True,
                    accept=",".join(constants.IMAGE_MIMETYPES),
                    aria_describedby="file-helper",
                ),
                Small("Image file: PNG, JPEG, WEBP or GIF.", id="file-helper"),
                components.get_text_input(None),
                components.get_listset_keyword_inputs(None),
                Input(type="submit", value="Add image"),
                action="/image/",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/")
async def post(
    request,
    title: str,
    upfile: UploadFile,
    text: str,
    listsets: list[str] = None,
    keywords: list[str] = None,
):
    "Actually add the image."
    filename = pathlib.Path(upfile.filename)
    if upfile.content_type not in constants.IMAGE_MIMETYPES:
        raise errors.Error("Cannot upload non-image file.")
    ext = filename.suffix
    if ext == ".md":
        raise errors.Error("Upload of Markdown file is disallowed.")
    image = items.Image()
    image.owner = request.scope["auth"]
    image.title = title.strip() or filename.stem
    filecontent = await upfile.read()
    filename = image.id + ext
    image.frontmatter["filename"] = filename
    try:
        with open(f"{constants.DATA_DIR}/{filename}", "wb") as outfile:
            outfile.write(filecontent)
    except OSError as error:
        raise errors.Error(error)
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
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(components.get_image_icon(), image.title),
                    Li(*components.get_item_links(image)),
                ),
                Ul(Li(components.search_form())),
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
            Div(
                components.get_listsets_card(image),
                components.get_keywords_card(image),
                cls="grid",
            ),
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
        Script("new ClipboardJS('.to_clipboard');", type="text/javascript"),
    )


@rt("/{image:Item}/edit")
def get(request, image: items.Item):
    "Form for editing metadata for the image."
    assert isinstance(image, items.Image)
    return (
        Title(f"Edit {image.title}"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(Strong("Edit "), image.title),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                components.get_title_input(image),
                Div(
                    Div(
                        Input(
                            type="file",
                            name="upfile",
                            aria_describedby="file-helper",
                        ),
                        Small("Image file: PNG, JPEG, WEBP or GIF.", id="file-helper"),
                        Img(
                            src=image.bin_url,
                            title=image.filename,
                            cls="display",
                        ),
                    ),
                    cls="grid",
                ),
                components.get_text_input(image),
                components.get_listset_keyword_inputs(image),
                Input(type="submit", value="Save"),
                action=f"{image.url}/edit",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
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
            raise errors.Error("Upload of Markdown file is disallowed.")
        filecontent = await upfile.read()
        filename = image.id + ext  # The mimetype may change on file contents update.
        try:
            with open(f"{constants.DATA_DIR}/{filename}", "wb") as outfile:
                outfile.write(filecontent)
        except OSError as error:
            raise errors.Error(error)
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
                    value="Copy image",
                ),
                action=f"{image.url}/copy",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/{source:Item}/copy")
def post(request, source: items.File, title: str):
    "Actually copy the image."
    assert isinstance(source, items.Image)
    filename = pathlib.Path(source.filename)
    image = items.Image()
    image.owner = request.scope["auth"]
    image.title = title.strip()
    image.text = source.text
    with open(source.filepath, "rb") as infile:
        filecontent = infile.read()
    filename = image.id + filename.suffix
    try:
        with open(f"{constants.DATA_DIR}/{filename}", "wb") as outfile:
            outfile.write(filecontent)
    except OSError as error:
        raise errors.Error(error)
    image.frontmatter["filename"] = filename
    image.keywords = source.keywords
    image.write()
    return components.redirect(image.url)


@rt("/{image:Item}/delete")
def get(request, image: items.Item):
    "Ask for confirmation to delete the file image."
    assert isinstance(image, items.Image)
    redirect = urllib.parse.urlsplit(request.headers["Referer"]).path
    if redirect == f"/image/{image.id}":
        redirect = "/images"
    return (
        Title(f"Delete {image.title}"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(Strong("Delete "), image.title),
                ),
            ),
            cls="container",
        ),
        Main(
            H3("Really delete the image? All data will be lost."),
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
                action=f"{image.url}/delete",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/{image:Item}/delete")
def post(image: items.Item, redirect: str):
    "Actually delete the image."
    assert isinstance(image, items.Image)
    image.delete()
    return components.redirect(redirect)
