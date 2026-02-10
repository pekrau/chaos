"Database item page."

import csv
from http import HTTPStatus as HTTP
import io
import sqlite3
import urllib.parse

from fasthtml.common import *

import components
import constants
import errors
import items

app, rt = components.get_app_rt()


@rt("/")
def get(request):
    "Form for creating a database."
    return (
        Title("Create database"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li("Create database"),
                ),
                cls="database",
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
                        Summary("Add to listsets..."),
                        Ul(*components.get_listsets_dropdown(None)),
                        cls="dropdown",
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
                        placeholder="Load Sqlite3 database File...",
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
                action="/database/",
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
    text: str,
    upfile: UploadFile = None,
    listsets: list[str] = None,
    keywords: list[str] = None,
):
    "Actually create the database."
    database = items.Database()
    # XXX For some reason, 'auth' is not set in 'request.scope'?
    database.owner = session["auth"]
    database.title = title.strip()
    database.frontmatter["filename"] = database.id + ".sqlite"
    if upfile.filename:
        try:
            with open(database.filepath, "wb") as outfile:
                outfile.write(await upfile.read())
        except OSError as error:
            raise errors.Error(error)
    try:
        cnx = sqlite3.connect(database.filepath)
    except sqlite3.Error as error:
        raise errors.Error(error)
    cnx.close()
    database.text = text.strip()
    for id in listsets or list():
        listset = items.get(id)
        assert isinstance(listset, items.Listset)
        listset.add(database)
        listset.write()
    database.keywords = keywords or list()
    database.write()
    return components.redirect(database.url)


@rt("/{database:Item}")
def get(database: items.Item):
    "View the metadata for the database."
    assert isinstance(database, items.Database)
    if tables := database.tables():
        tables_cards = [
            Card(
                Header(
                    "Table ",
                    Strong(tablename),
                    " ",
                    A(
                        f"{table['count']} rows",
                        href=f"/database/{database.id}/rows/{tablename}",
                        role="button",
                        cls="thin",
                    ),
                    A(
                        "CSV",
                        href=f"/database/{database.id}/csv/{tablename}",
                        role="button",
                        cls="thin secondary",
                    ),
                    A(
                        "JSON",
                        href=f"/database/{database.id}/json/{tablename}",
                        role="button",
                        cls="thin secondary",
                    ),
                    A("Schema", href="#", role="button", cls="outline thin"),
                ),
                Table(
                    Thead(
                        Tr(
                            Th("Row"),
                            Th("Type"),
                            Th("Min"),
                            Th("Max"),
                        ),
                    ),
                    Tbody(
                        *[
                            Tr(
                                Td(row["name"]),
                                Td(row["type"]),
                                Td(row["min"]),
                                Td(row["max"]),
                            )
                            for row in table["rows"]
                        ]
                    ),
                    cls="compressed",
                ),
            )
            for tablename, table in tables.items()
        ]
    else:
        tables_cards = [Card(I("No tables defined."))]
    if views := database.views():
        views_cards = [
            Card(
                Header(
                    "View ",
                    Strong(viewname),
                    " ",
                    A(
                        f"{view['count']} rows",
                        href=f"/database/{database.id}/rows/{viewname}",
                        role="button",
                        cls="thin",
                    ),
                    A(
                        "CSV",
                        href=f"/database/{database.id}/csv/{viewname}",
                        role="button",
                        cls="thin secondary",
                    ),
                    A(
                        "JSON",
                        href=f"/database/{database.id}/json/{viewname}",
                        role="button",
                        cls="thin secondary",
                    ),
                    A("Schema", href="#", role="button", cls="outline thin"),
                ),
                Table(
                    Thead(
                        Tr(
                            Th("Row"),
                            Th("Type"),
                            Th("Min"),
                            Th("Max"),
                        ),
                    ),
                    Tbody(
                        *[
                            Tr(
                                Td(row["name"]),
                                Td(row["type"]),
                                Td(row["min"]),
                                Td(row["max"]),
                            )
                            for row in view["rows"]
                        ]
                    ),
                    cls="compressed",
                ),
            )
            for viewname, view in views.items()
        ]
    else:
        views_cards = [Card(I("No views defined."))]
    return (
        Title(database.title),
        Script(src="/clipboard.min.js"),
        Script("new ClipboardJS('.to_clipboard');"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(components.get_database_icon(), Strong(database.title)),
                    Li(*components.get_item_links(database)),
                ),
                Ul(Li(components.search_form())),
                cls="database",
            ),
            cls="container",
        ),
        Main(
            Card(
                Strong(
                    A(
                        components.get_file_icon(),
                        database.filename,
                        href=database.bin_url,
                        title="Download Sqlite file",
                    )
                ),
            ),
            *tables_cards,
            *views_cards,
            components.get_text_card(database),
            components.get_listsets_card(database),
            components.get_keywords_card(database),
            cls="container",
        ),
        Footer(
            Hr(),
            Div(
                Div(database.modified_local),
                Div(f"{database.size:,d} + {database.file_size:,d} bytes"),
                Div(database.owner),
                cls="grid",
            ),
            cls="container",
        ),
    )


@rt("/{database:Item}/rows/{name}")
def get(request, database: items.Item, name: str):
    "Display row values from table or view."
    assert isinstance(database, items.Database)
    info = database.get_info(name)
    title = f"{database.title}; {info['type']} {name}"
    rows = database.cnx.execute(f"SELECT * FROM {name}").fetchall()
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(components.get_database_icon(), Strong(title)),
                ),
                Ul(Li(components.search_form())),
                cls="database",
            ),
            cls="container",
        ),
        Main(
            Table(
                Thead(
                    Tr(*[Th(row["name"], Br(), row["type"]) for row in info["rows"]])
                ),
                Tbody(*[Tr(*[Td(i) for i in row]) for row in rows]),
                cls="compressed",
                id="rows",
            ),
            cls="container",
        ),
        Footer(
            Hr(),
            Div(
                Div(database.modified_local),
                Div(f"{database.size:,d} + {database.file_size:,d} bytes"),
                Div(database.owner),
                cls="grid",
            ),
            cls="container",
        ),
    )


@rt("/{database:Item}/csv/{name:str}")
def get(request, database: items.Item, name: str):
    info = database.get_info(name)
    outfile = io.StringIO()
    writer = csv.writer(
        outfile, dialect="unix", delimiter=",", quoting=csv.QUOTE_NONNUMERIC
    )
    header = [row["name"] for row in info["rows"]]
    writer.writerow(header)
    writer.writerows(database.cnx.execute(f"SELECT {','.join(header)} FROM {name}"))
    return Response(
        content=outfile.getvalue(),
        status_code=HTTP.OK,
        headers={
            "Content-Type": constants.CSV_MIMETYPE,
            "Content-Disposition": f'attachment; filename="{name}.csv"',
        },
    )


@rt("/{database:Item}/json/{name:str}")
def get(request, database: items.Item, name: str):
    info = database.get_info(name)
    header = [row["name"] for row in info["rows"]]
    return {
        "$id": f"database {database.id}; {info['type']} {name}",
        "data": [
            dict(zip(header, row))
            for row in database.cnx.execute(f"SELECT {','.join(header)} FROM {name}")
        ],
    }


@rt("/{database:Item}/edit")
def get(request, database: items.Item):
    "Form for editing metadata for the database."
    assert isinstance(database, items.Database)
    return (
        Title("Edit"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Edit '{database.title}'"),
                ),
                cls="database",
            ),
            cls="container",
        ),
        Main(
            Form(
                Div(
                    Input(
                        type="text",
                        name="title",
                        value=database.title,
                        required=True,
                        placeholder="Title...",
                    ),
                    Details(
                        Summary("Add to listsets..."),
                        Ul(*components.get_listsets_dropdown(database)),
                        cls="dropdown",
                    ),
                    Details(
                        Summary("Keywords..."),
                        Ul(*components.get_keywords_dropdown(database.keywords)),
                        cls="dropdown",
                    ),
                    cls="grid",
                ),
                Div(
                    Label(
                        Span(
                            "Current database: ",
                            A(database.filename, href=database.bin_url),
                        ),
                        Input(
                            type="file",
                            name="upfile",
                        ),
                    ),
                    cls="grid",
                ),
                Textarea(
                    database.text,
                    name="text",
                    rows=10,
                    autofocus=True,
                ),
                Input(
                    type="submit",
                    value="Save",
                ),
                action=f"{database.url}/edit",
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


@rt("/{database:Item}/edit")
async def post(
    database: items.Item,
    title: str,
    upfile: UploadFile,
    text: str,
    listsets: list[str] = None,
    keywords: list[str] = None,
):
    "Actually edit the database."
    assert isinstance(database, items.Database)
    database.title = title.strip() or database.filename.stem
    if upfile.filename:
        ext = pathlib.Path(upfile.filename).suffix
        if ext == ".md":
            raise errors.Error("Upload of Markdown file is disallowed.")
        filecontent = await upfile.read()
        filename = database.id + ext  # The mimetype may change on file contents update.
        try:
            with open(f"{constants.DATA_DIR}/{filename}", "wb") as outfile:
                outfile.write(filecontent)
        except OSError as error:
            raise errors.Error(error)
    database.text = text.strip()
    for id in listsets or list():
        listset = items.get(id)
        assert isinstance(listset, items.Listset)
        listset.add(database)
        listset.write()
    database.keywords = keywords or list()
    database.write()
    return components.redirect(database.url)


@rt("/{database:Item}/copy")
def get(request, database: items.Item):
    "Form for making a copy of the database."
    assert isinstance(database, items.Database)
    return (
        Title("Copy"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Copy '{database.title}'"),
                ),
                cls="database",
            ),
            cls="container",
        ),
        Main(
            Form(
                Input(
                    type="text",
                    name="title",
                    value=database.title,
                    placeholder="Title...",
                    required=True,
                    autofocus=True,
                ),
                Input(
                    type="submit",
                    value="Save",
                ),
                action=f"{database.url}/copy",
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


@rt("/{source:Item}/copy")
def post(session, source: items.Database, title: str):
    "Actually copy the database."
    assert isinstance(source, items.Database)
    databasename = pathlib.Path(source.databasename)
    database = items.Database()
    # XXX For some reason, 'auth' is not set in 'request.scope'?
    database.owner = session["auth"]
    database.title = title.strip() or databasename.stem
    database.text = source.text
    with open(source.filepath, "rb") as infile:
        filecontent = infile.read()
    filename = database.id + filename.suffix
    try:
        with open(f"{constants.DATA_DIR}/{filename}", "wb") as outfile:
            outfile.write(filecontent)
    except OSError as error:
        raise errors.Error(error)
    database.frontmatter["filename"] = filename
    database.keywords = source.keywords
    database.write()
    return components.redirect(database.url)


@rt("/{database:Item}/delete")
def get(request, database: items.Item):
    "Ask for confirmation to delete the database."
    assert isinstance(database, items.Database)
    target = urllib.parse.urlsplit(request.headers["Referer"]).path
    if target == f"/database/{database.id}":
        target = "/databases"
    return (
        Title("Delete"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Delete '{database.title}'"),
                ),
                cls="database",
            ),
            cls="container",
        ),
        Main(
            P("Really delete the database? All data will be lost."),
            Form(
                Input(
                    type="submit",
                    value="Yes, delete",
                ),
                Input(
                    type="hidden",
                    name="target",
                    value=target,
                ),
                action=f"{database.url}/delete",
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


@rt("/{database:Item}/delete")
def post(database: items.Item, target: str):
    "Actually delete the database."
    assert isinstance(database, items.Database)
    database.delete()
    return components.redirect(target)
