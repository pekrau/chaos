"File entry pages."

import mimetypes
import pathlib

from fasthtml.common import *
import marko

import components
import constants
from entries import Entry, File


app, rt = components.fast_app()


@rt("/")
def get(session):
    "Form for adding a file."
    return (
        Title("chaos"),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
                    Li("Add file"),
                ),
                style=constants.FILE_NAV_STYLE,
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
                    placeholder="File...",
                    required=True,
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
                action="/file/",
                method="POST",
                enctype="multipart/form-data",
            ),
            cls="container",
        ),
    )


@rt("/")
async def post(session, title: str, upfile: UploadFile, text: str):
    "Actually add the file."
    filename = pathlib.Path(upfile.filename)
    ext = filename.suffix
    if ext == ".md":
        raise components.Error("Upload of Markdown file is disallowed")
    file = File()
    # XXX For some reason, 'auth' is not set in 'request.scope'?
    file.owner = session["auth"]
    file.title = title.strip() or filename.stem
    file.content = text.strip()
    filecontent = await upfile.read()
    filename = file.eid + ext
    try:
        with open(f"{constants.DATA_DIR}/{filename}", "wb") as outfile:
            outfile.write(filecontent)
    except OSError as error:
        raise components.Error(error)
    file.frontmatter["filename"] = filename
    file.write()
    return Redirect(file.url)


@rt("/{file:Entry}")
def get(session, file: Entry):
    "View the metadata for the file."
    assert isinstance(file, File)
    if file.filename.suffix.lower() in constants.IMAGE_SUFFIXES:
        image = Img(
            src=f"{file.url}/download", style="border: 1px solid #ddd; padding: 4px;"
        )
    else:
        image = ""
    return (
        Title(file.title),
        Script(src="/clipboard.min.js"),
        Script("new ClipboardJS('.to_clipboard');"),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
                    Li(components.get_entry_clipboard(file)),
                    Li(Strong(file.title)),
                    Li(A("Edit", role="button", href=f"{file.url}/edit")),
                    Li(A("Copy", role="button", href=f"{file.url}/copy")),
                    Li(
                        A(
                            "Delete",
                            role="button",
                            href=f"{file.url}/delete",
                            cls="outline",
                        )
                    ),
                ),
                Ul(
                    Li(components.search_form()),
                    Li(
                        Details(
                            Summary("Add..."),
                            Ul(
                                Li(A("Note", href="/note")),
                                Li(A("Link", href="/link")),
                                Li(A("File", href="/file")),
                            ),
                            cls="dropdown",
                        ),
                    ),
                ),
                style=constants.FILE_NAV_STYLE,
            ),
            cls="container",
        ),
        Main(
            Card(
                P(Strong(A(file.filename, href=f"{file.url}/download"))),
                P(image),
            ),
            NotStr(marko.convert(file.content)),
            cls="container",
        ),
        Footer(
            Hr(),
            Div(
                Div(f"{file.size:,d} + {file.filesize:,d} bytes"),
                Div(file.modified_local),
                cls="grid",
            ),
            cls="container",
        ),
    )


@rt("/{file:Entry}/download")
def get(session, file: Entry):
    "Download the file."
    media_type, encoding = mimetypes.guess_type(file.filename)
    headers = {"Content-Disposition": f'attachment; filename="{file.filename}"'}
    if encoding:
        headers["Content-Encoding"] = encoding
    return Response(
        content=file.filepath.read_bytes(),
        media_type=media_type or constants.BINARY_MEDIA_TYPE,
        headers=headers,
    )


@rt("/{file:Entry}/edit")
def get(session, file: Entry):
    "Form for editing metadata for a file."
    assert isinstance(file, File)
    return (
        Title("chaos"),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
                    Li(f"Edit file"),
                    Li(Strong(file.title)),
                ),
                style=constants.FILE_NAV_STYLE,
            ),
            cls="container",
        ),
        Main(
            Form(
                Input(
                    type="text",
                    name="title",
                    value=file.title,
                    required=True,
                ),
                Input(
                    type="file",
                    name="upfile",
                ),
                Textarea(
                    file.content,
                    name="text",
                    rows=10,
                    autofocus=True,
                ),
                Input(
                    type="submit",
                    value="Save",
                ),
                action=f"{file.url}/edit",
                method="POST",
            ),
            Form(
                Input(
                    type="submit",
                    value="Cancel",
                    cls="secondary",
                ),
                action=file.url,
                method="GET",
            ),
            cls="container",
        ),
    )


@rt("/{file:Entry}/edit")
async def post(session, file: Entry, title: str, upfile: UploadFile, text: str):
    "Actually edit the file."
    assert isinstance(file, File)
    if upfile.filename:
        ext = pathlib.Path(upfile.filename).suffix
        if ext == ".md":
            raise components.Error("Upload of Markdown file is disallowed")
        filecontent = await upfile.read()
        filename = file.eid + ext
        try:
            with open(f"{constants.DATA_DIR}/{filename}", "wb") as outfile:
                outfile.write(filecontent)
        except OSError as error:
            raise components.Error(error)
    file.title = title.strip() or file.filename.stem
    file.content = text.strip()
    file.write()
    return Redirect(file.url)


@rt("/{file:Entry}/copy")
def get(session, file: Entry):
    "Form for making a copy of the file."
    assert isinstance(file, File)
    return (
        Title("chaos"),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
                    Li("Copy file"),
                    Li(Strong(file.title)),
                ),
                style=constants.FILE_NAV_STYLE,
            ),
            cls="container",
        ),
        Main(
            Form(
                Input(
                    type="text",
                    name="title",
                    value=file.title,
                    required=True,
                ),
                Input(
                    type="url",
                    name="href",
                    value=file.href,
                ),
                Textarea(
                    file.content,
                    name="text",
                    rows=10,
                    autofocus=True,
                ),
                Input(
                    type="submit",
                    value="Save",
                ),
                action=f"/file",
                method="POST",
            ),
            Form(
                Input(
                    type="submit",
                    value="Cancel",
                    cls="secondary",
                ),
                action=file.url,
                method="GET",
            ),
            cls="container",
        ),
    )


@rt("/{file:Entry}/delete")
def get(session, file: Entry):
    "Ask for confirmation to delete the file."
    assert isinstance(file, File)
    return (
        Title(file.title),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
                    Li("File"),
                    Li(Strong(file.title)),
                ),
                style=constants.FILE_NAV_STYLE,
            ),
            cls="container",
        ),
        Main(
            P("Really delete the file? All data will be lost."),
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
                action=f"{file.url}/delete",
                method="POST",
            ),
            cls="container",
        ),
        Footer(
            Hr(),
            Div(
                Div(f"{file.size:,d} + {file.filesize:,d} bytes"),
                Div(file.modified_local),
                cls="grid",
            ),
            cls="container",
        ),
    )


@rt("/{file:Entry}/delete")
def post(session, file: Entry, action: str):
    "Actually delete the file."
    assert isinstance(file, File)
    if "yes" in action.casefold():
        file.delete()
        return Redirect(f"/")
    else:
        return Redirect(file.url)
