"Image entry pages."

import mimetypes
import pathlib

from fasthtml.common import *
import marko

import components
import constants
import entries


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
                Input(
                    type="text",
                    name="title",
                    placeholder="Title...",
                    autofocus=True,
                ),
                Input(
                    type="file",
                    name="upfile",
                    placeholder="image...",
                    required=True,
                    accept=",".join(constants.IMAGE_MIMETYPES),
                ),
                Textarea(
                    name="text",
                    rows=10,
                    placeholder="Text...",
                ),
                Select(
                    Option("Process request", selected=True, disabled=True, value=""),
                    Option("Extract text from image", value="extract_text"),
                    name="process",
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
                action=request.headers.get("Referer", "/"),
                method="GET",
            ),
            cls="container",
        ),
    )


@rt("/")
async def post(session, title: str, upfile: UploadFile, text: str, process: str = ""):
    "Actually add the image."
    filename = pathlib.Path(upfile.filename)
    if upfile.content_type not in constants.IMAGE_MIMETYPES:
        raise components.Error("Cannot upload non-image file.")
    ext = filename.suffix
    if ext == ".md":
        raise components.Error("Upload of Markdown file is disallowed.")
    image = entries.Image()
    # XXX For some reason, 'auth' is not set in 'request.scope'?
    image.owner = session["auth"]
    image.title = title.strip() or filename.stem
    image.text = text.strip()
    filecontent = await upfile.read()
    filename = str(image) + ext
    try:
        with open(f"{constants.DATA_DIR}/{filename}", "wb") as outfile:
            outfile.write(filecontent)
    except OSError as error:
        raise components.Error(error)
    image.frontmatter["filename"] = filename
    if process:
        image.frontmatter["process"] = process
    image.write()
    entries.set_keywords_relations(image)
    return components.redirect(image.url)


@rt("/{image:Entry}")
def get(image: entries.Entry):
    "View the metadata for the image."
    assert isinstance(image, entries.Image)
    if process := image.frontmatter.get("process", ""):
        process = Card(f"Process request: {process}")
    return (
        Title(image.title),
        Script(src="/clipboard.min.js"),
        Script("new ClipboardJS('.to_clipboard');"),
        Header(
            Nav(
                Ul(
                    Li(
                        components.get_nav_menu(
                            A(Strong("Edit"), href=f"{image.url}/edit"),
                            A(Strong("Copy"), href=f"{image.url}/copy"),
                            A(Strong("Delete"), href=f"{image.url}/delete"),
                        )
                    ),
                    Li(components.get_entry_clipboard(image), image.title),
                    Li(components.search_form()),
                ),
                cls="image",
            ),
            cls="container",
        ),
        Main(
            process,
            Card(
                A(
                    Img(src=f"{image.url}/data", title=image.filename, cls="display"),
                    href=f"{image.url}/data",
                )
            ),
            NotStr(marko.convert(image.text)),
            Small(
                Card(
                    Header("Keywords: ", components.get_keywords_links(image)),
                    components.get_entries_table(image.related()),
                ),
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
    )


@rt("/{image:Entry}/data")
def get(image: entries.Entry):
    "Return the image data."
    assert isinstance(image, entries.Image)
    return Response(
        content=image.filepath.read_bytes(),
        media_type=image.file_mimetype or constants.BINARY_MIMETYPE,
    )


@rt("/{image:Entry}/edit")
def get(image: entries.Entry):
    "Form for editing metadata for the image."
    assert isinstance(image, entries.Image)
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
                Fieldset(
                    Label(
                        "Title",
                        Input(
                            type="text",
                            name="title",
                            value=image.title,
                            required=True,
                        ),
                    ),
                    Label(
                        "Image",
                        Input(
                            type="file",
                            name="upfile",
                        ),
                        A(
                            Img(
                                src=f"{image.url}/data",
                                title=image.filename,
                                cls="display",
                            ),
                            href=f"{image.url}/data",
                        ),
                    ),
                    Label(
                        "Text",
                        Textarea(
                            image.text,
                            name="text",
                            rows=10,
                            autofocus=True,
                        ),
                    ),
                    Label(
                        "Process request",
                        Select(
                            Option("None", selected=True, disabled=True, value=""),
                            Option("Extract text from image", value="extract_text"),
                            name="process",
                        ),
                    ),
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
                action=image.url,
                method="GET",
            ),
            cls="container",
        ),
    )


@rt("/{image:Entry}/edit")
async def post(
    image: entries.Entry, title: str, upfile: UploadFile, text: str, process: str = None
):
    "Actually edit the image."
    assert isinstance(image, entries.Image)
    if upfile.filename:
        ext = pathlib.Path(upfile.filename).suffix
        if ext == ".md":
            raise components.Error("Upload of Markdown file is disallowed.")
        filecontent = await upfile.read()
        filename = str(image) + ext  # The mimetype may change on file contents update.
        try:
            with open(f"{constants.DATA_DIR}/{filename}", "wb") as outfile:
                outfile.write(filecontent)
        except OSError as error:
            raise components.Error(error)
    image.title = title.strip() or image.filename.stem
    text = text.strip()
    image.text = text
    if process:
        image.frontmatter["process"] = process
    image.write()
    entries.set_keywords_relations(image)
    return components.redirect(image.url)


@rt("/{image:Entry}/copy")
def get(image: entries.Entry):
    "Form for making a copy of the image."
    assert isinstance(image, entries.Image)
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
                Fieldset(
                    Label(
                        "Title",
                        Input(
                            type="text",
                            name="title",
                            value=image.title,
                            required=True,
                        ),
                    ),
                    Label(
                        "Image",
                        Input(
                            type="text",
                            value=image.filename,
                            readonly=True,
                        ),
                        Small("Cannot be changed."),
                    ),
                    Label(
                        "Text",
                        Textarea(
                            image.text,
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
                action=f"/image/{image}/copy",
                method="POST",
            ),
            Form(
                Input(
                    type="submit",
                    value="Cancel",
                    cls="secondary",
                ),
                action=image.url,
                method="GET",
            ),
            cls="container",
        ),
    )


@rt("/{source:Entry}/copy")
def post(session, source: entries.File, title: str, text: str):
    "Actually copy the image."
    assert isinstance(source, entries.Image)
    filename = pathlib.Path(source.filename)
    image = entries.Image()
    # XXX For some reason, 'auth' is not set in 'request.scope'?
    image.owner = session["auth"]
    image.title = title.strip() or filename.stem
    image.text = text.strip()
    with open(source.filepath, "rb") as infile:
        filecontent = infile.read()
    filename = str(image) + filename.suffix
    try:
        with open(f"{constants.DATA_DIR}/{filename}", "wb") as outfile:
            outfile.write(filecontent)
    except OSError as error:
        raise components.Error(error)
    image.frontmatter["filename"] = filename
    image.write()
    entries.set_keywords_relations(image)
    return components.redirect(image.url)


@rt("/{image:Entry}/delete")
def get(image: entries.Entry):
    "Ask for confirmation to delete the file image."
    assert isinstance(image, entries.Image)
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
                action=f"{image.url}/delete",
                method="POST",
            ),
            cls="container",
        ),
    )


@rt("/{image:Entry}/delete")
def post(image: entries.Entry, action: str):
    "Actually delete the image."
    assert isinstance(image, entries.Image)
    if "yes" in action.casefold():
        image.delete()
        return components.redirect(f"/")
    else:
        return components.redirect(image.url)
