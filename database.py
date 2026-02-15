"Database item page."

import csv
from http import HTTPStatus as HTTP
import io
import json
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
                    value="Add database",
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
    if database.plots:
        plots = [
            Div(A(p["title"], href=f"/database/{database.id}/plot/{p['name']}"))
            for p in database.plots
        ]
    else:
        plots = [I("None.")]
    return (
        Title(database.title),
        Script(src="/clipboard.min.js"),
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
            components.get_text_card(database),
            Card(get_database_overview(database)),
            Card(
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
                Div(
                    Div(
                        A(
                            components.get_file_icon(),
                            "Sqlite binary file",
                            href=database.bin_url,
                            cls="secondary",
                            title="Download Sqlite file",
                        ),
                    ),
                    Div(
                        A(
                            components.get_icon("filetype-sql.svg"),
                            "SQL text file",
                            href=f"/database/{database.id}/sql",
                            cls="secondary",
                            title="Download SQL file",
                        ),
                        style="margin-top: 0.5em;",
                    ),
                    cls="right",
                ),
                cls="grid",
            ),
            Card(
                Header("Plots"),
                *plots,
            ),
            Div(
                components.get_listsets_card(database),
                components.get_keywords_card(database),
                cls="grid",
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
        Script("new ClipboardJS('.to_clipboard');", type="text/javascript"),
    )


@rt("/{database:Item}/sql")
def get(database: items.Item):
    "Download the database in SQL format."
    assert isinstance(database, items.Database)
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
def get(session, request, database: items.Item, name: str):
    "Add a row to the table."
    assert isinstance(database, items.Database)
    info = database.get_tableview_info(name)
    inputs = []
    for column in info["columns"]:
        label = [Strong(column["name"]), ", ", column["type"]]
        if not column["null"]:
            label.append(", NOT NULL")
        if column["primary"]:
            label.append(", PRIMARY KEY")
        kwargs = dict(
            name=column["name"], required=not column["null"], autofocus=not bool(inputs)
        )
        if column["type"] == "INTEGER":
            inputs.append((Div(*label), Input(type="number", step="1", **kwargs)))
        elif column["type"] == "REAL":
            inputs.append((Div(*label), Input(type="number", **kwargs)))
        else:
            inputs.append((Div(*label), Input(type="text", **kwargs)))
    return (
        Title(f"Add row to table {name}"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li("Add row to table ", Strong(name)),
                ),
            ),
            cls="container",
        ),
        Main(
            Card(
                Div(
                    components.get_database_icon(),
                    A(database.title, href=database.url),
                ),
                A(
                    f"{info['count']} rows",
                    href=f"/database/{database.id}/rows/{name}",
                    role="button",
                    cls="thin",
                ),
                cls="grid",
            ),
            Form(
                Fieldset(*[Label(i[0], i[1]) for i in inputs]),
                Input(type="submit", value="Add row"),
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
def post(session, database: items.Item, name: str, form: dict):
    "Actually add the row to the table."
    assert isinstance(database, items.Database)
    info = database.get_tableview_info(name)
    columns = []
    values = []
    try:
        for column in info["columns"]:
            columns.append(column["name"])
            if column["type"] == "INTEGER":
                if value := form[column["name"]]:
                    value = int(value)
                elif column["null"]:
                    value = None
                else:
                    raise ValueError(f"{column['name']} requries a value")
            elif column["type"] == "REAL":
                if value := form[column["name"]]:
                    value = float(value)
                elif column["null"]:
                    value = None
                else:
                    raise ValueError(f"{column['name']} requries a value")
            else:
                if value := form[column["name"]]:
                    pass
                elif column["null"]:
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
    add_toast(session, "Row added.", "success")
    return components.redirect(f"/database/{database.id}/row/{name}")


@rt("/{database:Item}/rows/{name}")
def get(database: items.Item, name: str):
    "Display row values from table or view."
    assert isinstance(database, items.Database)
    info = database.get_tableview_info(name)
    title = f"{info['type'].capitalize()} {name}"
    with database as cnx:
        rows = cnx.execute(f"SELECT * FROM {name}").fetchall()
    db_items = [
        Div(
            components.get_database_icon(),
            A(database.title, href=database.url),
        ),
        Div(
            Button(
                f"{info['count']} rows",
                cls="secondary outline thin",
                style="margin-left: 1em;",
            ),
            A(
                "Add row",
                href=f"/database/{database.id}/row/{name}",
                role="button",
                cls="thin",
                style="margin-left: 1em;",
            ),
        ),
        Div(
            A(
                components.get_file_icon(constants.CSV_MIMETYPE),
                "CSV",
                href=f"/database/{database.id}/csv/{name}",
                cls="secondary",
                style="margin-left: 1em;",
                title="Download CSV file",
            ),
            A(
                components.get_file_icon(constants.JSON_MIMETYPE),
                "JSON",
                href=f"/database/{database.id}/json/{name}",
                cls="secondary",
                style="margin-left: 1em;",
                title="Download JSON file",
            ),
            cls="right",
        ),
    ]
    table_items = Tr(*[Th(column["name"]) for column in info["columns"]])
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
            Card(
                Header(*db_items, cls="grid"),
                Table(
                    Thead(table_items),
                    Tbody(*[Tr(*[Td(i) for i in row]) for row in rows]),
                    Tfoot(table_items),
                    cls="compressed",
                    id="rows",
                ),
                Footer(*db_items, cls="grid"),
                cls="container",
            ),
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


@rt("/{database:Item}/csv")
def get(request, database: items.Item):
    assert isinstance(database, items.Database)
    title = "Create table from CSV file"
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
            Card(
                components.get_database_icon(),
                A(database.title, href=database.url),
            ),
            Form(
                Fieldset(
                    Label(
                        "Table name",
                        Input(
                            type="text",
                            name="name",
                            required=True,
                        ),
                    ),
                    Label(
                        "CSV file (must contain header)",
                        Input(
                            type="file",
                            name="upfile",
                        ),
                    ),
                ),
                Input(
                    type="submit",
                    value="Upload",
                ),
                action=f"{database.url}/csv",
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


@rt("/{database:Item}/csv")
async def post(request, database: items.Item, name: str, upfile: UploadFile):
    assert isinstance(database, items.Database)
    content = await upfile.read()
    reader = csv.reader(io.StringIO(content.decode("utf-8")))
    header = next(reader)
    rows = list(reader)
    columns = []
    for pos, columnname in enumerate(header):
        column = dict(name=columnname, type="INTEGER", null=False)
        columns.append(column)
        try:
            for row in rows:
                if value := row[pos]:
                    row[pos] = int(value)
                else:
                    row[pos] = None
                    column["null"] = True
        except ValueError:
            try:
                for row in rows:
                    if value := row[pos]:
                        row[pos] = float(value)
                    else:
                        row[pos] = None
                        column["null"] = True
                column["type"] = "REAL"
            except ValueError:
                for row in rows:
                    if not value:
                        row[pos] = None
                        column["null"] = True
                column["type"] = "TEXT"
    for column in columns:
        column["sql"] = (
            f"{column['name']} {column['type']} {'' if column['null'] else 'NOT NULL'}"
        )
    try:
        with database as cnx:
            sql = ", ".join([c["sql"] for c in columns])
            cnx.execute(f"CREATE TABLE {name} ({sql})")
            sql = f"({', '.join([c['name'] for c in columns])}) VALUES ({', '.join(['?'] * len(columns))})"
            cnx.executemany(f"INSERT INTO {name} {sql}", rows)
    except sqlite3.Error as error:
        raise errors.Error(error)
    return components.redirect(database.url)


@rt("/{database:Item}/csv/{name:str}")
def get(database: items.Item, name: str):
    "Download the table or view in CSV format."
    assert isinstance(database, items.Database)
    info = database.get_tableview_info(name)
    outfile = io.StringIO()
    writer = csv.writer(outfile, quoting=csv.QUOTE_MINIMAL)
    column_names = [column["name"] for column in info["columns"]]
    writer.writerow(column_names)
    with database as cnx:
        writer.writerows(cnx.execute(f"SELECT {','.join(column_names)} FROM {name}"))
    outfile.seek(0)
    content = outfile.read().encode("utf-8")
    return Response(
        headers={
            "Content-Type": f"{constants.CSV_MIMETYPE}; charset=utf-8",
            "Content-Disposition": f'attachment; filename="{database.id}_{name}.csv"',
        },
        content=content,
        status_code=HTTP.OK,
    )


@rt("/{database:Item}/json/{name:str}")
def get(database: items.Item, name: str):
    "Get the table or view in JSON format."
    assert isinstance(database, items.Database)
    info = database.get_tableview_info(name)
    column_names = [column["name"] for column in info["columns"]]
    with database as cnx:
        rows = cnx.execute(f"SELECT {','.join(column_names)} FROM {name}").fetchall()
    return {
        "$id": f"database {database.id}; {info['type']} {name}",
        "data": [dict(zip(column_names, row)) for row in rows],
    }


@rt("/{database:Item}/execute")
def post(database: items.Item, sql: str = None):
    "Execute a SQL command."
    assert isinstance(database, items.Database)
    column_names = []
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
                    column_names = [t[0] for t in cursor.description]
    if column_names or result:
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
                Thead(*[Tr(*[Th(c) for c in column_names])]),
                Tbody(*[Tr(*[Td(v) for v in row]) for row in result]),
            ),
        )
    else:
        result_card = ""
    return (
        Title(f"SQL command in database {database.title} "),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(
                        "SQL command in database ",
                        Strong(database.title),
                    ),
                ),
            ),
            cls="container",
        ),
        Main(
            Card(
                Header(
                    components.get_database_icon(),
                    A(database.title, href=database.url),
                ),
                get_database_overview(database, full=True),
            ),
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
    with database as cnx:
        try:
            cursor = cnx.execute(sql)
        except sqlite3.Error as error:
            errors.Error(str(error))
        else:
            header = [t[0] for t in cursor.description]
            rows = cursor.fetchall()
    outfile = io.StringIO()
    writer = csv.writer(outfile, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(header)
    writer.writerows(rows)
    outfile.seek(0)
    content = outfile.read().encode("utf-8")
    return Response(
        content=content,
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
                column_names = [t[0] for t in cursor.description]
            rows = cursor.fetchall()
    return {
        "$id": f"database {database.id}",
        "query": sql,
        "data": [dict(zip(column_names, row)) for row in rows],
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
                    value="Copy database",
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


@rt("/{database:Item}/plot")
def get(session, request, database: items.Item):
    "Add a plot to the database."
    assert isinstance(database, items.Database)
    return (
        Title(f"Add a plot to the database {database.title}"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Add a plot to the database ", Strong(database.title)),
                ),
            ),
            cls="container",
        ),
        Main(
            Card(
                Header(
                    components.get_database_icon(),
                    A(database.title, href=database.url),
                ),
                get_database_overview(database),
            ),
            Form(
                Fieldset(
                    Legend(
                        "Type of plot",
                        Label(
                            Input(type="radio", name="type", value="scatter"), "Scatter"
                        ),
                        Label(Input(type="radio", name="type", value="line"), "Line"),
                        Label(
                            Input(type="radio", name="type", value="barchart"),
                            "Bar chart",
                        ),
                        Label(
                            Input(type="radio", name="type", value="piechart"),
                            "Pie chart",
                        ),
                    ),
                ),
                Input(type="submit", value="Add plot"),
                action=f"/database/{database.id}/plot",
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


@rt("/{database:Item}/plot")
def post(session, request, database: items.Item):
    "Actually add a plot to the database."
    assert isinstance(database, items.Database)
    raise NotImplementedError


def get_database_overview(database, full=False):
    "Get an overview of the basic structure of the database."
    rows = []
    items = list(database.tables().items()) + list(database.views().items())
    for name, item in items:
        spec = [
            Li(
                f"{r['name']} {r['type']} {not r['null'] and 'NOT NULL' or ''} {r['primary'] and 'PRIMARY KEY' or ''}"
            )
            for r in item["columns"]
        ]
        spec.append(Li(item["sql"]))
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
                    cls="top",
                ),
                Td(
                    Details(
                        Summary("Schema", role="button", cls="thin outline"),
                        Ul(*spec),
                        open=full,
                    ),
                ),
                Td(
                    A(
                        f"{item['count']} rows",
                        href=f"/database/{database.id}/rows/{name}",
                        role="button",
                        cls="thin",
                    ),
                    add_row,
                    cls="top",
                ),
                Td(
                    A(
                        components.get_file_icon(constants.CSV_MIMETYPE),
                        "CSV",
                        href=f"/database/{database.id}/csv/{name}",
                        cls="secondary",
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
