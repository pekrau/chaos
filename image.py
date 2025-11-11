"Image entry pages."

from http import HTTPStatus as HTTP
import mimetypes
import pathlib

from fasthtml.common import *
import marko

import components
import constants
import entries
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
                        type="file",
                        name="upfile",
                        placeholder="image...",
                        required=True,
                        accept=",".join(constants.IMAGE_MIMETYPES),
                    ),
                    Details(
                        Summary("Process request..."),
                        Ul(
                            Li(
                                Label(
                                    Input(
                                        type="radio",
                                        name="process",
                                        value="none",
                                        checked=True,
                                    ),
                                    "None",
                                ),
                            ),
                            Li(
                                Label(
                                    Input(
                                        type="radio",
                                        name="process",
                                        value="extract_text",
                                    ),
                                    "Extract text from image",
                                ),
                            ),
                        ),
                        cls="dropdown",
                    ),
                    cls="grid",
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
async def post(
    session,
    title: str,
    upfile: UploadFile,
    text: str,
    keywords: list[str] = [],
    process: str = "",
):
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
    filecontent = await upfile.read()
    filename = str(image) + ext
    image.frontmatter["filename"] = filename
    try:
        with open(f"{constants.DATA_DIR}/{filename}", "wb") as outfile:
            outfile.write(filecontent)
    except OSError as error:
        raise components.Error(error)
    image.text = text.strip()
    image.keywords = keywords
    if process and process != "none":
        image.frontmatter["process"] = process
    image.write()
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
                    Li(
                        components.get_entry_edit(image),
                        " ",
                        components.get_entry_link_to_clipboard(image),
                    ),
                ),
                Ul(Li(components.search_form())),
                cls="image",
            ),
            cls="container",
        ),
        Main(
            process,
            Card(
                A(
                    Img(src=image.data_url, title=image.filename, cls="display"),
                    href=image.data_url,
                )
            ),
            NotStr(marko.convert(image.text)),
            components.get_keywords_entries_card(image),
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
                    Input(
                        type="text",
                        name="title",
                        value=image.title,
                        required=True,
                        placeholder="Title...",
                    ),
                    Details(
                        Summary("Keywords..."),
                        Ul(*components.get_keywords_dropdown(image.keywords)),
                        cls="dropdown",
                    ),
                    cls="grid",
                ),
                Fieldset(
                    Div(
                        Input(
                            type="file",
                            name="upfile",
                        ),
                        Img(
                            src=image.data_url,
                            title=image.filename,
                            cls="display",
                        ),
                    ),
                    Details(
                        Summary("Process request..."),
                        Ul(
                            Li(
                                Label(
                                    Input(
                                        type="radio",
                                        name="process",
                                        value="none",
                                        checked=True,
                                    ),
                                    "None",
                                ),
                            ),
                            Li(
                                Label(
                                    Input(
                                        type="radio",
                                        name="process",
                                        value="extract_text",
                                    ),
                                    "Extract text from image",
                                ),
                            ),
                        ),
                        cls="dropdown",
                    ),
                    cls="grid",
                ),
                Fieldset(
                    Textarea(
                        image.text,
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
    image: entries.Entry,
    title: str,
    upfile: UploadFile,
    text: str,
    keywords: list[str] = [],
    process: str = None,
):
    "Actually edit the image."
    assert isinstance(image, entries.Image)
    image.title = title.strip() or image.filename.stem
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
    image.text = text.strip()
    image.keywords = keywords
    if process and process != "none":
        image.frontmatter["process"] = process
    else:
        image.frontmatter.pop("process", None)
    image.write()
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
                    Input(
                        type="text",
                        name="title",
                        value=image.title,
                        placeholder="Title...",
                        required=True,
                        autofocus=True,
                    ),
                ),
                Input(
                    type="submit",
                    value="Copy",
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
def post(session, source: entries.File, title: str):
    "Actually copy the image."
    assert isinstance(source, entries.Image)
    filename = pathlib.Path(source.filename)
    image = entries.Image()
    # XXX For some reason, 'auth' is not set in 'request.scope'?
    image.owner = session["auth"]
    image.title = title.strip()
    image.text = source.text
    with open(source.filepath, "rb") as infile:
        filecontent = infile.read()
    filename = str(image) + filename.suffix
    try:
        with open(f"{constants.DATA_DIR}/{filename}", "wb") as outfile:
            outfile.write(filecontent)
    except OSError as error:
        raise components.Error(error)
    image.frontmatter["filename"] = filename
    image.keywords = source.keywords
    image.write()
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
