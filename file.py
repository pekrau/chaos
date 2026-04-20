"File item pages."

import pathlib
import urllib.parse

from fasthtml.common import *

import components
import constants
import errors
import items

app, rt = components.get_app_rt()


@rt("/")
def get():
    "Form for adding a file."
    title = "Add file"
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
                Input(type="file", name="upfile", required=True),
                components.get_text_input(),
                components.get_tags_input(),
                Input(type="submit", value="Add file"),
                action="/file/",
                method="POST",
            ),
            components.get_cancel_form("/"),
            cls="container",
        ),
    )


@rt("/")
async def post(title: str, upfile: UploadFile, text: str, tags: list[str] = None):
    "Actually add the file."
    filename = pathlib.Path(upfile.filename)
    ext = filename.suffix
    if ext == ".md":
        raise errors.Error("Upload of Markdown file is disallowed.")
    file = items.File()
    file.title = title.strip() or filename.stem
    filecontent = await upfile.read()
    filename = file.id + ext
    file.frontmatter["filename"] = filename
    try:
        with open(f"{constants.DATA_DIR}/{filename}", "wb") as outfile:
            outfile.write(filecontent)
    except OSError as error:
        raise errors.Error(error)
    file.text = text.strip()
    file.tags = tags
    file.write()
    return components.redirect(file.url)


@rt("/{file:Item}")
def get(file: items.Item, page: int = 1, tags_page: int = 1, refs_page: int = 1):
    "View the data for the file."
    assert isinstance(file, items.File)
    return (
        Title(file.title),
        components.get_clipboard_script(),
        # Non-standard header.
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(file)),
                    Li(
                        components.get_file_icon(file.file_mimetype, title="File"),
                        file.title,
                    ),
                    Li(components.get_to_clipboard(file)),
                ),
                Ul(
                    Li(components.get_search()),
                ),
            ),
            cls="container",
        ),
        Main(
            Card(Strong(A(file.filename, href=file.url_file))),
            components.get_text_card(file),
            Form(
                components.get_refs_card(file, refs_page),
                components.get_tags_card(file, tags_page),
                action=file.url,
            ),
            cls="container",
        ),
        components.get_footer_item_view(
            file, size=f"{file.size:,d} + {file.file_size:,d} bytes"
        ),
        components.get_clipboard_activate(),
    )


@rt("/{file:Item}{ext:Ext}")
def get(file: items.Item, ext: str):
    "Download the content of the file."
    assert isinstance(file, items.File)
    if file.filepath.suffix == ext:
        return FileResponse(file.filepath)
    else:
        raise errors.Error("invalid format", HTTP.NOT_FOUND)


@rt("/{file:Item}/edit")
def get(file: items.Item):
    "Form for editing the data for the file."
    assert isinstance(file, items.File)
    return (
        *components.get_header_item_edit(file),
        Main(
            Form(
                components.get_title_input(file.title),
                Div(
                    Label(
                        Span("Current file: ", A(file.filename, href=file.url_file)),
                        Input(
                            type="file",
                            name="upfile",
                        ),
                    ),
                    cls="grid",
                ),
                components.get_text_input(file.text),
                components.get_tags_input(file.tags),
                Input(type="submit", value="Save"),
                action=f"{file.url}/edit",
                method="POST",
            ),
            components.get_cancel_form(file.url),
            cls="container",
        ),
    )


@rt("/{file:Item}/edit")
async def post(
    file: items.Item, title: str, upfile: UploadFile, text: str, tags: list[str] = None
):
    "Actually edit the file."
    assert isinstance(file, items.File)
    if upfile.filename:
        ext = pathlib.Path(upfile.filename).suffix
        if ext == ".md":
            raise errors.Error("Upload of Markdown file is disallowed.")
        filecontent = await upfile.read()
        filename = file.id + ext  # The mimetype may change on file contents update.
        try:
            with open(f"{constants.DATA_DIR}/{filename}", "wb") as outfile:
                outfile.write(filecontent)
        except OSError as error:
            raise errors.Error(error)
    file.title = title.strip()
    file.text = text.strip()
    file.tags = tags
    file.write()
    return components.redirect(file.url)


@rt("/{file:Item}/copy")
def get(file: items.Item):
    "Form for making a copy of the file."
    assert isinstance(file, items.File)
    title = f"Copy '{file.title}'"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(file)),
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
                    value=file.title,
                    placeholder="Title...",
                    required=True,
                ),
                Input(type="submit", value="Copy file"),
                action=f"{file.url}/copy",
                method="POST",
            ),
            components.get_cancel_form(file.url),
            cls="container",
        ),
    )


@rt("/{source:Item}/copy")
def post(source: items.File, title: str):
    "Actually copy the file."
    assert isinstance(source, items.File)
    filename = pathlib.Path(source.filename)
    file = items.File()
    file.title = title.strip() or filename.stem
    file.text = source.text
    with open(source.filepath, "rb") as infile:
        filecontent = infile.read()
    filename = file.id + filename.suffix
    try:
        with open(f"{constants.DATA_DIR}/{filename}", "wb") as outfile:
            outfile.write(filecontent)
    except OSError as error:
        raise errors.Error(error)
    file.frontmatter["filename"] = filename
    file.write()
    return components.redirect(file.url)


@rt("/{file:Item}/delete")
def get(file: items.Item):
    "Ask for confirmation to delete the file."
    assert isinstance(file, items.File)
    title = f"Delete '{file.title}'"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(file)),
                    Li(title),
                ),
            ),
            cls="container",
        ),
        Main(
            H3("Really delete the file? All data will be lost."),
            Form(
                Input(type="submit", value="Yes, delete"),
                action=f"{file.url}/delete",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/{file:Item}/delete")
def post(file: items.Item):
    "Actually delete the file."
    assert isinstance(file, items.File)
    file.delete()
    return components.redirect()
