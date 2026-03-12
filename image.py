"Image item pages."

from http import HTTPStatus as HTTP
import pathlib
import urllib.parse


from fasthtml.common import *

import components
import constants
import errors
import items

app, rt = components.get_app_rt()


@rt("/")
def get(request):
    "Form for adding an image."
    title = "Add image"
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
                Input(
                    type="file",
                    name="upfile",
                    required=True,
                    accept=",".join(constants.IMAGE_MIMETYPES),
                    aria_describedby="file-helper",
                ),
                Small("Image file: PNG, JPEG, SVG, WEBP or GIF.", id="file-helper"),
                components.get_text_input(),
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
    image.text = text.strip()
    filecontent = await upfile.read()
    filename = image.id + ext
    image.frontmatter["filename"] = filename
    try:
        with open(f"{constants.DATA_DIR}/{filename}", "wb") as outfile:
            outfile.write(filecontent)
    except OSError as error:
        raise errors.Error(error)
    image.write()
    return components.redirect(image.url)


@rt("/{image:Item}")
def get(session, image: items.Item):
    "View the data for the image."
    assert isinstance(image, items.Image)
    return (
        Title(image.title),
        components.clipboard_script(),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(image)),
                    Li(components.get_image_icon(), image.title),
                    Li(components.to_clipboard(image)),
                ),
                Ul(
                    Li(components.get_recent_menu(session, image)),
                ),
            ),
            cls="container",
        ),
        Main(
            Card(
                A(
                    Img(src=image.url_file, title=image.filename, cls="display"),
                    href=image.url_file,
                )
            ),
            components.get_text_card(image),
            components.get_xrefs_card(image),
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
        components.clipboard_activate(),
    )


@rt("/{image:Item}{ext:Ext}")
def get(image: items.Item, ext: str):
    "Download the content of the image."
    assert isinstance(image, items.Image)
    if image.filepath.suffix == ext:
        return FileResponse(image.filepath)
    else:
        raise errors.Error("invalid format", HTTP.NOT_FOUND)


@rt("/{image:Item}/edit")
def get(request, image: items.Item):
    "Form for editing the data for the image."
    assert isinstance(image, items.Image)
    title = f"Edit {image.title}"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(image)),
                    Li(title),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                components.get_title_input(image.title),
                Div(
                    Div(
                        Input(
                            type="file",
                            name="upfile",
                            aria_describedby="file-helper",
                        ),
                        Small(
                            "Image file: PNG, JPEG, SVG, WEBP or GIF.", id="file-helper"
                        ),
                        Img(
                            src=image.url_file,
                            title=image.filename,
                            cls="display",
                        ),
                    ),
                    cls="grid",
                ),
                components.get_text_input(image.text),
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
):
    "Actually edit the image."
    assert isinstance(image, items.Image)
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
    image.title = title.strip()
    image.text = text.strip()
    image.write()
    return components.redirect(image.url)


@rt("/{image:Item}/copy")
def get(request, image: items.Item):
    "Form for making a copy of the image."
    assert isinstance(image, items.Image)
    title = f"Copy '{image.title}'"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(image)),
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
                    value=image.title,
                    placeholder="Title...",
                    required=True,
                ),
                Input(type="submit", value="Copy image"),
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
    image.write()
    return components.redirect(image.url)


@rt("/{image:Item}/delete")
def get(request, image: items.Item):
    "Ask for confirmation to delete the file image."
    assert isinstance(image, items.Image)
    redirect = urllib.parse.urlsplit(request.headers["Referer"]).path
    if redirect == f"/image/{image.id}":
        redirect = "/images"
    title = f"Delete '{image.title}'"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(image)),
                    Li(title),
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
                Input(type="submit", value="Yes, delete"),
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
