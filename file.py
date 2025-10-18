"File entry pages."

import pathlib

from fasthtml.common import *
import marko

import components
import constants
import entries


app, rt = components.get_app_rt()


@rt("/")
def get(request):
    "Form for adding a file."
    return (
        Title("Add file"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li("Add file"),
                ),
                cls="file",
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
                Select(
                    Option("Process request", selected=True, disabled=True, value=""),
                    Option("Extract text from image", value="extract_text"),
                    Option(
                        "Extract keywords from PDF, DOCX or EPUB",
                        value="extract_keywords",
                    ),
                    Option(
                        "Extract Markdown text from PDF, DOCX or EPUB",
                        value="extract_markdown",
                    ),
                    name="process",
                ),
                Input(
                    type="submit",
                    value="Save",
                ),
                action="/file/",
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
    "Actually add the file."
    filename = pathlib.Path(upfile.filename)
    ext = filename.suffix
    if ext == ".md":
        raise components.Error("Upload of Markdown file is disallowed.")
    file = entries.File()
    # XXX For some reason, 'auth' is not set in 'request.scope'?
    file.owner = session["auth"]
    file.title = title.strip() or filename.stem
    file.text = text.strip()
    filecontent = await upfile.read()
    filename = str(file) + ext
    try:
        with open(f"{constants.DATA_DIR}/{filename}", "wb") as outfile:
            outfile.write(filecontent)
    except OSError as error:
        raise components.Error(error)
    file.frontmatter["filename"] = filename
    if process:
        file.frontmatter["process"] = process
    file.write()
    entries.set_keywords_relations(file)
    return components.redirect(file.url)


@rt("/{file:Entry}")
def get(file: entries.Entry):
    "View the metadata for the file."
    assert isinstance(file, entries.File)
    if file.is_image():
        display = A(
            Img(src=f"{file.url}/data", title=file.filename, cls="display"),
            href=f"{file.url}/data",
        )
    else:
        display = Strong(A(file.filename, href=f"{file.url}/data"))
    if process := file.frontmatter.get("process", ""):
        process = Card(f"Process request: {process}")
    return (
        Title(file.title),
        Script(src="/clipboard.min.js"),
        Script("new ClipboardJS('.to_clipboard');"),
        Header(
            Nav(
                Ul(
                    Li(
                        components.get_nav_menu(
                            A(Strong("Edit"), href=f"{file.url}/edit"),
                            A(Strong("Copy"), href=f"{file.url}/copy"),
                            A(Strong("Delete"), href=f"{file.url}/delete"),
                        )
                    ),
                    Li(components.get_entry_clipboard(file), file.title),
                    Li(components.search_form()),
                ),
                cls="file",
            ),
            cls="container",
        ),
        Main(
            process,
            Card(display),
            NotStr(marko.convert(file.text)),
            Small(
                Card(
                    Header("Keywords: ", components.get_keywords_links(file)),
                    components.get_entries_table(file.related()),
                ),
            ),
            cls="container",
        ),
        Footer(
            Hr(),
            Div(
                Div(file.modified_local),
                Div(f"{file.size:,d} + {file.file_size:,d} bytes"),
                Div(file.owner),
                cls="grid",
            ),
            cls="container",
        ),
    )


@rt("/{file:Entry}/data")
def get(file: entries.Entry):
    "Return the file data."
    return Response(
        content=file.filepath.read_bytes(),
        media_type=file.file_mimetype or constants.BINARY_MIMETYPE,
    )


@rt("/{file:Entry}/edit")
def get(file: entries.Entry):
    "Form for editing metadata for a file."
    assert isinstance(file, entries.File)
    return (
        Title("Edit"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Edit '{file.title}'"),
                ),
                cls="file",
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
                            value=file.title,
                            required=True,
                        ),
                    ),
                    Label(
                        "File",
                        Input(
                            type="file",
                            name="upfile",
                        ),
                        Small(f"Current file: {file.filename}"),
                    ),
                    Label(
                        "Text",
                        Textarea(
                            file.text,
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
                            Option(
                                "Extract keywords from PDF, DOCX or EPUB",
                                value="extract_keywords",
                            ),
                            Option(
                                "Extract Markdown text from PDF, DOCX or EPUB",
                                value="extract_markdown",
                            ),
                            name="process",
                        ),
                    ),
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
async def post(
    file: entries.Entry, title: str, upfile: UploadFile, text: str, process: str = None
):
    "Actually edit the file."
    assert isinstance(file, entries.File)
    if upfile.filename:
        ext = pathlib.Path(upfile.filename).suffix
        if ext == ".md":
            raise components.Error("Upload of Markdown file is disallowed.")
        filecontent = await upfile.read()
        filename = str(file) + ext  # The mimetype may change on file contents update.
        try:
            with open(f"{constants.DATA_DIR}/{filename}", "wb") as outfile:
                outfile.write(filecontent)
        except OSError as error:
            raise components.Error(error)
    file.title = title.strip() or file.filename.stem
    text = text.strip()
    file.text = text
    if process:
        file.frontmatter["process"] = process
    file.write()
    entries.set_keywords_relations(file)
    return components.redirect(file.url)


@rt("/{file:Entry}/copy")
def get(file: entries.Entry):
    "Form for making a copy of the file."
    assert isinstance(file, entries.File)
    return (
        Title("Copy"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Copy '{file.title}'"),
                ),
                cls="file",
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
                            value=file.title,
                            required=True,
                        ),
                    ),
                    Label(
                        "File",
                        Input(
                            type="text",
                            value=file.filename,
                            readonly=True,
                        ),
                        Small("Cannot be changed."),
                    ),
                    Label(
                        "Text",
                        Textarea(
                            file.text,
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
                action=f"/file/{file}/copy",
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


@rt("/{sourcefile:Entry}/copy")
def post(session, sourcefile: entries.File, title: str, text: str):
    "Actually copy the file."
    assert isinstance(sourcefile, entries.File)
    filename = pathlib.Path(sourcefile.filename)
    file = entries.File()
    # XXX For some reason, 'auth' is not set in 'request.scope'?
    file.owner = session["auth"]
    file.title = title.strip() or filename.stem
    file.text = text.strip()
    with open(sourcefile.filepath, "rb") as infile:
        filecontent = infile.read()
    filename = str(file) + filename.suffix
    try:
        with open(f"{constants.DATA_DIR}/{filename}", "wb") as outfile:
            outfile.write(filecontent)
    except OSError as error:
        raise components.Error(error)
    file.frontmatter["filename"] = filename
    file.write()
    entries.set_keywords_relations(file)
    return components.redirect(file.url)


@rt("/{file:Entry}/delete")
def get(file: entries.Entry):
    "Ask for confirmation to delete the file."
    assert isinstance(file, entries.File)
    return (
        Title("Delete"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Delete '{file.title}'"),
                ),
                cls="file",
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
    )


@rt("/{file:Entry}/delete")
def post(file: entries.Entry, action: str):
    "Actually delete the file."
    assert isinstance(file, entries.File)
    if "yes" in action.casefold():
        file.delete()
        return components.redirect(f"/")
    else:
        return components.redirect(file.url)
