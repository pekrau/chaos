"File entry pages."

import mimetypes
import pathlib

from fasthtml.common import *
import marko

import components
import constants
import entries


app, rt = components.get_app_rt()


@rt("/")
def get(session):
    "Form for adding a file."
    return (
        Title("Add file"),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
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
                Input(
                    type="submit",
                    value="Save",
                ),
                action="/file/",
                method="POST",
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
        raise components.Error("Upload of Markdown file is disallowed.")
    file = entries.File()
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
    entries.set_keywords_relations(file)
    return components.redirect(file.url)


@rt("/{file:Entry}")
def get(session, file: entries.Entry):
    "View the metadata for the file."
    assert isinstance(file, entries.File)
    if file.filename.suffix.lower() in constants.IMAGE_SUFFIXES:
        image = Img(src=f"{file.url}/download", cls="display")
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
                    Li(Strong(file.title)),
                    Li(
                        components.get_dropdown_menu(
                            A(
                                "Link to clipboard",
                                data_clipboard_action="copy",
                                data_clipboard_text=f"[{file.title}]({file.url})",
                                cls="to_clipboard",
                                href="#",
                            ),
                            A("Edit", href=f"{file.url}/edit"),
                            A("Copy", href=f"{file.url}/copy"),
                            A("Delete", href=f"{file.url}/delete"),
                            A("Add note...", href="/note"),
                            A("Add link...", href="/link"),
                            A("Add file...", href="/file"),
                            A("Keywords", href="/keywords"),
                        ),
                    ),
                    Li(components.search_form()),
                ),
                cls="file",
            ),
            cls="container",
        ),
        Main(
            Card(
                P(Strong(A(file.filename, href=f"{file.url}/download"))),
                P(image),
            ),
            NotStr(marko.convert(file.content)),
            Small(
                Card(
                    Header("Keywords: ", components.get_keywords_links(file)),
                    components.get_entries_table(file.related()),
                ),
            ),
            cls="container",
        ),
        components.get_footer(
            f"{file.size:,d} + {file.filesize:,d} bytes", file.modified_local
        ),
    )


@rt("/{file:Entry}/download")
def get(session, file: entries.Entry):
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
def get(session, file: entries.Entry):
    "Form for editing metadata for a file."
    assert isinstance(file, entries.File)
    return (
        Title("Edit"),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
                    Li(f"Edit"),
                    Li(Strong(file.title)),
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
                    ),
                    Label(
                        "Text",
                        Textarea(
                            file.content,
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
async def post(session, file: entries.Entry, title: str, upfile: UploadFile, text: str):
    "Actually edit the file."
    assert isinstance(file, entries.File)
    if upfile.filename:
        ext = pathlib.Path(upfile.filename).suffix
        if ext == ".md":
            raise components.Error("Upload of Markdown file is disallowed.")
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
    entries.set_keywords_relations(file)
    return components.redirect(file.url)


@rt("/{file:Entry}/copy")
def get(session, file: entries.Entry):
    "Form for making a copy of the file."
    assert isinstance(file, entries.File)
    return (
        Title("Copy"),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
                    Li("Copy"),
                    Li(Strong(file.title)),
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
                        "File (cannot be changed)",
                        Input(
                            type="text",
                            value=file.filename,
                            readonly=True,
                        ),
                    ),
                    Label(
                        "Text",
                        Textarea(
                            file.content,
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
def get(session, file: entries.Entry):
    "Ask for confirmation to delete the file."
    assert isinstance(file, entries.File)
    return (
        Title("Delete"),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
                    Li("Delete"),
                    Li(Strong(file.title)),
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
        components.get_footer(
            f"{file.size:,d} + {file.filesize:,d} bytes", file.modified_local
        ),
    )


@rt("/{file:Entry}/delete")
def post(session, file: entries.Entry, action: str):
    "Actually delete the file."
    assert isinstance(file, entries.File)
    if "yes" in action.casefold():
        file.delete()
        return components.redirect(f"/")
    else:
        return components.redirect(file.url)
