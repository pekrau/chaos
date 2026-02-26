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
def get(request):
    "Form for adding a file."
    return (
        Title("Add file"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(components.get_file_icon(), "Add file"),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                components.get_title_input(None),
                Input(type="file", name="upfile", required=True),
                components.get_text_input(None),
                components.get_listset_keyword_inputs(None),
                Input(type="submit", value="Add file"),
                action="/file/",
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
    "Actually add the file."
    filename = pathlib.Path(upfile.filename)
    ext = filename.suffix
    if ext == ".md":
        raise errors.Error("Upload of Markdown file is disallowed.")
    file = items.File()
    file.owner = request.scope["auth"]
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
    for id in listsets or list():
        listset = items.get(id)
        assert isinstance(listset, items.Listset)
        listset.add(file)
        listset.write()
    file.keywords = keywords or list()
    file.write()
    return components.redirect(file.url)


@rt("/{file:Item}")
def get(file: items.Item):
    "View the data for the file."
    assert isinstance(file, items.File)
    return (
        Title(file.title),
        Script(src="/clipboard.min.js"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(
                        components.get_file_icon(file.file_mimetype, title="File"),
                        file.title,
                    ),
                    Li(*components.get_item_links(file)),
                ),
                Ul(Li(components.search_form())),
            ),
            cls="container",
        ),
        Main(
            Card(A(file.filename, href=file.bin_url)),
            components.get_text_card(file),
            Div(
                components.get_listsets_card(file),
                components.get_keywords_card(file),
                cls="grid",
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
        Script("new ClipboardJS('.to_clipboard');", type="text/javascript"),
    )


@rt("/{file:Item}/edit")
def get(request, file: items.Item):
    "Form for editing the data for the file."
    assert isinstance(file, items.File)
    return (
        Title(f"Edit {file.title}"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(Strong("Edit "), file.title),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                components.get_title_input(file),
                Div(
                    Label(
                        Span("Current file: ", A(file.filename, href=file.bin_url)),
                        Input(
                            type="file",
                            name="upfile",
                        ),
                    ),
                    cls="grid",
                ),
                components.get_text_input(file),
                components.get_listset_keyword_inputs(file),
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
    file: items.Item,
    title: str,
    upfile: UploadFile,
    text: str,
    listsets: list[str] = None,
    keywords: list[str] = None,
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
    file.edit(title, text, listsets, keywords)
    file.write()
    return components.redirect(file.url)


@rt("/{file:Item}/copy")
def get(request, file: items.Item):
    "Form for making a copy of the file."
    assert isinstance(file, items.File)
    return (
        Title("Copy"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Copy '{file.title}'"),
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
                    autofocus=True,
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
def post(request, source: items.File, title: str):
    "Actually copy the file."
    assert isinstance(source, items.File)
    filename = pathlib.Path(source.filename)
    file = items.File()
    file.owner = request.scope["auth"]
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
    file.keywords = source.keywords
    file.write()
    return components.redirect(file.url)


@rt("/{file:Item}/delete")
def get(request, file: items.Item):
    "Ask for confirmation to delete the file."
    assert isinstance(file, items.File)
    redirect = urllib.parse.urlsplit(request.headers["Referer"]).path
    if redirect == f"/file/{file.id}":
        redirect = "/files"
    return (
        Title(f"Delete {file.title}"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(Strong("Delete "), file.title),
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
