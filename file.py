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
                Input(type="submit", value="Add file"),
                action="/file/",
                method="POST",
            ),
            components.get_cancel_form("/"),
            cls="container",
        ),
    )


@rt("/")
async def post(title: str, upfile: UploadFile, text: str):
    "Actually add the file."
    filename = pathlib.Path(upfile.filename)
    ext = filename.suffix
    if ext == ".md":
        raise errors.Error("Upload of Markdown file is disallowed.")
    file = items.File()
    file.title = title.strip() or filename.stem
    file.text = text.strip()
    filecontent = await upfile.read()
    filename = file.id + ext
    file.frontmatter["filename"] = filename
    try:
        with open(f"{constants.DATA_DIR}/{filename}", "wb") as outfile:
            outfile.write(filecontent)
    except OSError as error:
        raise errors.Error(error)
    file.write()
    return components.redirect(file.url)


@rt("/{file:Item}")
def get(file: items.Item):
    "View the data for the file."
    assert isinstance(file, items.File)
    return (
        Title(file.title),
        components.clipboard_script(),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(file)),
                    Li(
                        components.get_file_icon(file.file_mimetype, title="File"),
                        file.title,
                    ),
                    Li(components.to_clipboard(file)),
                ),
                Ul(
                    Li(components.get_shortcuts_menu(file)),
                ),
            ),
            cls="container",
        ),
        Main(
            Card(Strong(A(file.filename, href=file.url_file))),
            components.get_text_card(file),
            components.get_tags_card(file),
            components.get_refs_card(file),
            cls="container",
        ),
        Footer(
            Hr(),
            Div(
                Div(file.modified_local),
                Div(f"{file.size:,d} + {file.file_size:,d} bytes"),
                Div(A("Source", href=f"/source/{file.id}"), cls="right"),
                cls="grid",
            ),
            cls="container",
        ),
        components.clipboard_activate(),
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
def get(request, file: items.Item):
    "Form for editing the data for the file."
    assert isinstance(file, items.File)
    title = f"Edit '{file.title}'"
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
            components.get_cancel_form(request.headers["Referer"]),
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
def get(request, file: items.Item):
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
            components.get_cancel_form(request.headers["Referer"]),
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
def get(request, file: items.Item):
    "Ask for confirmation to delete the file."
    assert isinstance(file, items.File)
    redirect = urllib.parse.urlsplit(request.headers["Referer"]).path
    if redirect == f"/file/{file.id}":
        redirect = "/"
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
                Input(
                    type="hidden",
                    name="redirect",
                    value=redirect,
                ),
                Input(type="submit", value="Yes, delete"),
                action=f"{file.url}/delete",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/{file:Item}/delete")
def post(file: items.Item, redirect: str):
    "Actually delete the file."
    assert isinstance(file, items.File)
    file.delete()
    return components.redirect(redirect)
