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
    "Form for adding a database."
    return (
        Title("Add database"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(components.get_database_icon(), "Add database"),
                ),
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
                Input(
                    type="file",
                    name="upfile",
                    aria_describedby="file-helper",
                ),
                Small("Binary Sqlite3 database file (optional).", id="file-helper"),
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
    # Test that file really is an Sqlite3 file.
    try:
        cnx = sqlite3.connect(database.filepath)
    except sqlite3.Error as error:
        database.filepath.unlink()
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
            ),
            cls="container",
        ),
        Main(
            Card(get_database_overview(database, full=False)),
            Div(
                Form(
                    Input(type="submit", value="SQL command"),
                    action=f"/database/{database.id}/execute",
                    method="POST",
                ),
                Form(
                    Input(type="submit", value="Create table from CSV file"),
                    action=f"/database/{database.id}/csv",
                    method="GET",
                ),
                cls="grid",
            ),
            Card(
                Div(
                    A(
                        components.get_file_icon(),
                        database.filename,
                        href=database.bin_url,
                        title="Download Sqlite file",
                    ),
                    " (Sqlite binary file)",
                ),
                Div(
                    A(
                        components.get_icon("filetype-sql.svg"),
                        f"{database.id}.sql",
                        href=f"/database/{database.id}/sql",
                        title="Download SQL file",
                    ),
                    " (SQL text file)",
                ),
                cls="grid",
            ),
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


@rt("/{database:Item}/sql")
def get(database: items.Item):
    "Download the database in SQL format."
    outfile = io.StringIO()
    outfile.write(f"/* Database {database.id} */\n\n")
    with database as cnx:
        for line in cnx.iterdump():
            outfile.write(line)
            outfile.write("\n")
    return Response(
        content=outfile.getvalue(),
        status_code=HTTP.OK,
        headers={
            "Content-Type": constants.TEXT_MIMETYPE,
            "Content-Disposition": f'attachment; filename="{database.id}.sql"',
        },
    )


@rt("/{database:Item}/row/{name}")
def get(request, database: items.Item, name: str):
    "Add a row to the table."
    assert isinstance(database, items.Database)
    title = f"Add row to table {name}"
    info = database.get_info(name)
    inputs = []
    for row in info["rows"]:
        label = (
            f"{row['name']} {row['type']} {not row['null'] and 'NOT NULL' or ''} {row['primary'] and 'PRIMARY KEY' or ''}",
        )
        kwargs = dict(name=row["name"], required=not row["null"])
        if row["type"] == "INTEGER":
            inputs.append((label, Input(type="number", step="1", **kwargs)))
        elif row["type"] == "REAL":
            inputs.append((label, Input(type="number", **kwargs)))
        else:
            inputs.append((label, Input(type="text", **kwargs)))
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(Strong(title)),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                Fieldset(*[Label(i[0], i[1]) for i in inputs]),
                Input(
                    type="hidden", name="_redirect", value=request.headers["Referer"]
                ),
                Input(type="submit", value="Add"),
                action=f"/database/{database.id}/row/{name}",
                method="POST",
            ),
            Form(
                Input(
                    type="submit",
                    value="Cancel",
                    cls="secondary",
                ),
                action=f"/database/{database.id}",
                method="GET",
            ),
            cls="container",
        ),
    )


@rt("/{database:Item}/row/{name}")
def post(database: items.Item, name: str, _redirect: str, form: dict):
    "Actually add the row to the table."
    assert isinstance(database, items.Database)
    info = database.get_info(name)
    columns = []
    values = []
    try:
        for row in info["rows"]:
            columns.append(row["name"])
            if row["type"] == "INTEGER":
                if value := form[row["name"]]:
                    value = int(value)
                elif row["null"]:
                    value = None
                else:
                    raise ValueError(f"{row['name']} requries a value")
            elif row["type"] == "REAL":
                if value := form[row["name"]]:
                    value = float(value)
                elif row["null"]:
                    value = None
                else:
                    raise ValueError(f"{row['name']} requries a value")
            else:
                if value := form[row["name"]]:
                    pass
                elif row["null"]:
                    value = None
                else:
                    value = ""
            values.append(value)
    except (TypeError, ValueError) as error:
        raise errors.Error(error)
    with database as cnx:
        cnx.execute(
            f"INSERT INTO {name} ({','.join(columns)}) VALUES ({','.join('?' * len(values))})",
            values,
        )
    return components.redirect(_redirect)


@rt("/{database:Item}/rows/{name}")
def get(database: items.Item, name: str):
    "Display row values from table or view."
    assert isinstance(database, items.Database)
    info = database.get_info(name)
    title = f"{info['type'].capitalize()} {name}"
    with database as cnx:
        rows = cnx.execute(f"SELECT * FROM {name}").fetchall()
    db_card = Card(
        Div(components.get_database_icon(), A(database.title, href=database.url)),
        Div(
            A(
                "Add row",
                href=f"/database/{database.id}/row/{name}",
                role="button",
                cls="thin",
            ),
            Button(f"{len(rows)} rows", cls="secondary outline thin"),
            A(
                components.get_file_icon(constants.CSV_MIMETYPE),
                "CSV",
                href=f"/database/{database.id}/csv/{name}",
                cls="secondary",
                style="margin-left: 1em;",
            ),
            A(
                components.get_file_icon(constants.JSON_MIMETYPE),
                "JSON",
                href=f"/database/{database.id}/json/{name}",
                cls="secondary",
                style="margin-left: 1em;",
            ),
            cls="right",
        ),
        cls="grid",
    )
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(Strong(title)),
                ),
                Ul(Li(components.search_form())),
            ),
            cls="container",
        ),
        Main(
            db_card,
            Table(
                Thead(
                    Tr(*[Th(row["name"], Br(), row["type"]) for row in info["rows"]])
                ),
                Tbody(*[Tr(*[Td(i) for i in row]) for row in rows]),
                cls="compressed",
                id="rows",
            ),
            db_card,
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
def get(database: items.Item, name: str):
    "Download the table or view in CSV format."
    info = database.get_info(name)
    outfile = io.StringIO()
    writer = csv.writer(
        outfile, dialect="unix", delimiter=",", quoting=csv.QUOTE_NONNUMERIC
    )
    colnames = [row["name"] for row in info["rows"]]
    writer.writerow(colnames)
    with database as cnx:
        writer.writerows(cnx.execute(f"SELECT {','.join(colnames)} FROM {name}"))
    return Response(
        content=outfile.getvalue(),
        status_code=HTTP.OK,
        headers={
            "Content-Type": constants.CSV_MIMETYPE,
            "Content-Disposition": f'attachment; filename="{database.id}_{name}.csv"',
        },
    )


@rt("/{database:Item}/json/{name:str}")
def get(database: items.Item, name: str):
    "Get the table or view in JSON format."
    info = database.get_info(name)
    colnames = [row["name"] for row in info["rows"]]
    with database as cnx:
        rows = cnx.execute(f"SELECT {','.join(colnames)} FROM {name}").fetchall()
    return {
        "$id": f"database {database.id}; {info['type']} {name}",
        "data": [dict(zip(colnames, row)) for row in rows],
    }


@rt("/{database:Item}/execute")
def post(database: items.Item, sql: str = None):
    "Execute a SQL command."
    colnames = []
    result = []
    error_card = ""
    if sql:
        with database as cnx:
            try:
                cursor = cnx.execute(sql)
            except sqlite3.Error as error:
                error_card = Card(Header("Error", style="color: red;"), Pre(str(error)))
            else:
                result = cursor.fetchall()
                if cursor.description:
                    colnames = [t[0] for t in cursor.description]
                else:
                    colnames = []
    if colnames or result:
        result_card = Card(
            Header(
                Strong(f"{len(result)} rows", cls="center"),
                Form(
                    Input(type="hidden", name="sql", value=sql),
                    Input(
                        type="submit",
                        value="Download CSV",
                        cls="contrast",
                    ),
                    method="POST",
                    action=f"/database/{database.id}/execute/csv",
                ),
                Form(
                    Input(type="hidden", name="sql", value=sql),
                    Input(
                        type="submit",
                        value="Get JSON",
                        cls="contrast",
                    ),
                    method="POST",
                    action=f"/database/{database.id}/execute/json",
                ),
                cls="grid",
            ),
            Table(
                Thead(*[Tr(*[Th(c) for c in colnames])]),
                Tbody(*[Tr(*[Td(v) for v in row]) for row in result]),
            ),
        )
    else:
        result_card = ""
    return (
        Title(f"{database.title} SQL command"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(
                        components.get_database_icon(),
                        Strong(database.title),
                        " SQL command",
                    ),
                ),
            ),
            cls="container",
        ),
        Main(
            Card(get_database_overview(database)),
            Card(
                Form(
                    Fieldset(
                        Label("SQL command"),
                        Textarea(sql or "", name="sql", autofocus=True),
                    ),
                    Input(type="submit", value="Execute"),
                    action=f"/database/{database.id}/execute",
                    method="POST",
                ),
                Form(
                    Input(
                        type="submit",
                        value="Cancel",
                        cls="secondary",
                    ),
                    action=f"/database/{database.id}",
                    method="GET",
                ),
            ),
            error_card,
            result_card,
            cls="container",
        ),
    )


@rt("/{database:Item}/execute/csv")
def post(database: items.Item, sql: str):
    "Execute a SQL command and download the result as CSV."
    assert isinstance(database, items.Database)
    assert sql
    outfile = io.StringIO()
    writer = csv.writer(
        outfile, dialect="unix", delimiter=",", quoting=csv.QUOTE_NONNUMERIC
    )
    with database as cnx:
        try:
            cursor = cnx.execute(sql)
        except sqlite3.Error as error:
            errors.Error(str(error))
        else:
            if cursor.description:
                writer.writerow([t[0] for t in cursor.description])
            writer.writerows(cursor.fetchall())
    return Response(
        content=outfile.getvalue(),
        status_code=HTTP.OK,
        headers={
            "Content-Type": constants.CSV_MIMETYPE,
            "Content-Disposition": f'attachment; filename="query.csv"',
        },
    )


@rt("/{database:Item}/execute/json")
def post(database: items.Item, sql: str, filename: str = ""):
    "Execute a SQL command and return the result as JSON."
    assert isinstance(database, items.Database)
    assert sql
    with database as cnx:
        try:
            cursor = cnx.execute(sql)
        except sqlite3.Error as error:
            errors.Error(str(error))
        else:
            if cursor.description:
                colnames = [t[0] for t in cursor.description]
            rows = cursor.fetchall()
    return {
        "$id": f"database {database.id}",
        "query": sql,
        "data": [dict(zip(colnames, row)) for row in rows],
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
    redirect = urllib.parse.urlsplit(request.headers["Referer"]).path
    if redirect == f"/database/{database.id}":
        redirect = "/databases"
    return (
        Title("Delete"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Delete '{database.title}'"),
                ),
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
                    name="redirect",
                    value=redirect,
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
def post(database: items.Item, redirect: str):
    "Actually delete the database."
    assert isinstance(database, items.Database)
    database.delete()
    return components.redirect(redirect)


def get_database_overview(database, full=True):
    "Get an overview of the basic structure of the database."
    rows = []
    items = list(database.tables().items()) + list(database.views().items())
    for name, item in items:
        if full:
            columns = Ul(
                *[
                    Li(
                        f"{r['name']} {r['type']} {not r['null'] and 'NOT NULL' or ''} {r['primary'] and 'PRIMARY KEY' or ''}"
                    )
                    for r in item["rows"]
                ]
            )
        else:
            columns = ""
        if item["type"] == "table":
            add_row = A(
                "Add row",
                href=f"/database/{database.id}/row/{name}",
                role="button",
                cls="thin",
            )
        else:
            add_row = ""

        rows.append(
            Tr(
                Th(
                    f"{item['type'].capitalize()} ",
                    Strong(name),
                    columns,
                ),
                Td(
                    add_row,
                    A(
                        f"{item['count']} rows",
                        href=f"/database/{database.id}/rows/{name}",
                        role="button",
                        cls="thin",
                    ),
                    A(
                        components.get_file_icon(constants.CSV_MIMETYPE),
                        "CSV",
                        href=f"/database/{database.id}/csv/{name}",
                        cls="secondary",
                        style="margin-left: 1em;",
                    ),
                    A(
                        components.get_file_icon(constants.JSON_MIMETYPE),
                        "JSON",
                        href=f"/database/{database.id}/json/{name}",
                        cls="secondary",
                        style="margin-left: 1em;",
                    ),
                    cls="right top",
                ),
            ),
        )
    return Table(Tbody(*rows))
