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
                Div(
                    Input(
                        type="text",
                        name="title",
                        placeholder="Title...",
                        required=True,
                        autofocus=True,
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
                        placeholder="File...",
                        required=True,
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
                                        value="extract_keywords",
                                    ),
                                    "Extract keywords from PDF, DOCX or EPUB",
                                ),
                            ),
                            Li(
                                Label(
                                    Input(
                                        type="radio",
                                        name="process",
                                        value="extract_markdown",
                                    ),
                                    "Extract Markdown text from PDF, DOCX or EPUB",
                                ),
                            ),
                        ),
                        cls="dropdown",
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
                action="/file/",
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
    keywords: list[str] = None,
    process: str = "",
):
    "Actually add the file."
    filename = pathlib.Path(upfile.filename)
    ext = filename.suffix
    if ext == ".md":
        raise components.Error("Upload of Markdown file is disallowed.")
    file = entries.File()
    # XXX For some reason, 'auth' is not set in 'request.scope'?
    file.owner = session["auth"]
    file.title = title.strip() or filename.stem
    filecontent = await upfile.read()
    filename = file.id + ext
    file.frontmatter["filename"] = filename
    try:
        with open(f"{constants.DATA_DIR}/{filename}", "wb") as outfile:
            outfile.write(filecontent)
    except OSError as error:
        raise components.Error(error)
    file.text = text.strip()
    file.keywords = keywords or list()
    if process and process != "none":
        file.frontmatter["process"] = process
    file.write()
    return components.redirect(file.url)


@rt("/{file:Entry}")
def get(file: entries.Entry):
    "View the metadata for the file."
    assert isinstance(file, entries.File)
    if process := file.frontmatter.get("process", ""):
        process = Card(f"Process request: {process}")
    return (
        Title(file.title),
        Script(src="/clipboard.min.js"),
        Script("new ClipboardJS('.to_clipboard');"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(Strong(file.title)),
                    Li(*components.get_entry_links(file)),
                ),
                Ul(Li(components.search_form())),
                cls="file",
            ),
            cls="container",
        ),
        Main(
            process,
            Card(
                Strong(
                    A(
                        components.get_mimetype_icon(file.file_mimetype),
                        file.filename,
                        href=file.data_url,
                    )
                )
            ),
            NotStr(marko.convert(file.text)),
            components.get_keywords_entries_card(file),
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


@rt("/{file:Entry}/edit")
def get(request, file: entries.Entry):
    "Form for editing metadata for the file."
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
                Div(
                    Input(
                        type="text",
                        name="title",
                        value=file.title,
                        required=True,
                        placeholder="Title...",
                    ),
                    Details(
                        Summary("Keywords..."),
                        Ul(*components.get_keywords_dropdown(file.keywords)),
                        cls="dropdown",
                    ),
                    cls="grid",
                ),
                Div(
                    Label(
                        Span("Current file: ", A(file.filename, href=file.data_url)),
                        Input(
                            type="file",
                            name="upfile",
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
                                        value="extract_keywords",
                                    ),
                                    "Extract keywords from PDF, DOCX or EPUB",
                                ),
                            ),
                            Li(
                                Label(
                                    Input(
                                        type="radio",
                                        name="process",
                                        value="extract_markdown",
                                    ),
                                    "Extract Markdown text from PDF, DOCX or EPUB",
                                ),
                            ),
                        ),
                        cls="dropdown",
                    ),
                    cls="grid",
                ),
                Textarea(
                    file.text,
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
                action=request.headers["Referer"],
                method="GET",
            ),
            cls="container",
        ),
    )


@rt("/{file:Entry}/edit")
async def post(
    file: entries.Entry,
    title: str,
    upfile: UploadFile,
    text: str,
    keywords: list[str] = None,
    process: str = None,
):
    "Actually edit the file."
    assert isinstance(file, entries.File)
    file.title = title.strip() or file.filename.stem
    if upfile.filename:
        ext = pathlib.Path(upfile.filename).suffix
        if ext == ".md":
            raise components.Error("Upload of Markdown file is disallowed.")
        filecontent = await upfile.read()
        filename = file.id + ext  # The mimetype may change on file contents update.
        try:
            with open(f"{constants.DATA_DIR}/{filename}", "wb") as outfile:
                outfile.write(filecontent)
        except OSError as error:
            raise components.Error(error)
    file.text = text.strip()
    file.keywords = keywords or list()
    if process and process != "none":
        file.frontmatter["process"] = process
    else:
        file.frontmatter.pop("process", None)
    file.write()
    return components.redirect(file.url)


@rt("/{file:Entry}/copy")
def get(request, file: entries.Entry):
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
                Input(
                    type="text",
                    name="title",
                    value=file.title,
                    placeholder="Title...",
                    required=True,
                    autofocus=True,
                ),
                Input(
                    type="submit",
                    value="Save",
                ),
                action=f"{file.url}/copy",
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


@rt("/{source:Entry}/copy")
def post(session, source: entries.File, title: str):
    "Actually copy the file."
    assert isinstance(source, entries.File)
    filename = pathlib.Path(source.filename)
    file = entries.File()
    # XXX For some reason, 'auth' is not set in 'request.scope'?
    file.owner = session["auth"]
    file.title = title.strip() or filename.stem
    file.text = source.text
    with open(source.filepath, "rb") as infile:
        filecontent = infile.read()
    filename = file.id + filename.suffix
    try:
        with open(f"{constants.DATA_DIR}/{filename}", "wb") as outfile:
            outfile.write(filecontent)
    except OSError as error:
        raise components.Error(error)
    file.frontmatter["filename"] = filename
    file.keywords = source.keywords
    file.write()
    return components.redirect(file.url)


@rt("/{file:Entry}/delete")
def get(request, file: entries.Entry):
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
                Input(
                    type="submit",
                    value="Yes, delete",
                ),
                Input(
                    type="hidden",
                    name="target",
                    value=request.headers["Referer"],
                ),
                action=f"{file.url}/delete",
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


@rt("/{file:Entry}/delete")
def post(file: entries.Entry, target: str):
    "Actually delete the file."
    assert isinstance(file, entries.File)
    file.delete()
    return components.redirect(target)
