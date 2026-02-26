"Database item page."

import copy
import csv
import datetime
from http import HTTPStatus as HTTP
import io
import json
import sqlite3
import urllib.parse

import bokeh.embed
import bokeh.models
import bokeh.plotting
import bokeh.resources
from fasthtml.common import *
import numpy as np

import components
import constants
import errors
import items
from timer import Timer
import utils

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
                components.get_title_input(None),
                Input(
                    type="file",
                    name="upfile",
                    aria_describedby="file-helper",
                ),
                Small("Binary Sqlite3 database file (optional).", id="file-helper"),
                components.get_text_input(None),
                components.get_listset_keyword_inputs(None),
                Input(type="submit", value="Add database"),
                action="/database/",
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
    text: str,
    upfile: UploadFile = None,
    listsets: list[str] = None,
    keywords: list[str] = None,
):
    "Actually create the database."
    database = items.Database()
    database.owner = request.scope["auth"]
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
    "View the metadata and plots for the database."
    assert isinstance(database, items.Database)
    schema = database.get_schema()
    plot_rows = [
        Tr(
            Td(
                A(
                    plot["title"],
                    href=f"{database.url}/plot/{name}",
                )
            ),
            Td(plot["type"]),
            Td(
                A(
                    components.get_icon("pencil.svg", title=f"Edit {name}"),
                    href=f"{database.url}/plot/{name}/edit",
                ),
                A(
                    components.get_icon("copy.svg", title=f"Copy {name}"),
                    href=f"{database.url}/plot/{name}/copy",
                ),
                A(
                    components.get_icon("trash.svg", title=f"Delete {name}"),
                    href=f"{database.url}/plot/{name}/delete",
                ),
                cls="right",
            ),
        )
        for name, plot in database.plots.items()
    ]
    if plot_rows:
        plots_table = Table(
            Thead(
                Tr(
                    Th("Plot"),
                    Th("Type"),
                    Th(),
                ),
            ),
            Tbody(*plot_rows),
        )
    else:
        plots_table = I("None.")

    return (
        Title(database.title),
        Script(src="/clipboard.min.js"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(components.get_database_icon(), database.title),
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
                    action=f"{database.url}/execute",
                    method="POST",
                ),
                Form(
                    Input(type="submit", value="Upload CSV file"),
                    action=f"{database.url}/csv",
                    method="GET",
                ),
                Div(
                    A(
                        "Download Sqlite binary",
                        href=database.bin_url,
                        role="button",
                        cls="secondary outline",
                    ),
                ),
                Div(
                    A(
                        "Download SQL text",
                        href=f"{database.url}/sql",
                        role="button",
                        cls="secondary outline",
                    ),
                ),
                cls="grid",
            ),
            Card(
                Header("Plots"),
                plots_table,
                Footer(
                    Form(
                        Input(type="submit", value="Add plot"),
                        action=f"{database.url}/plot",
                        method="GET",
                    ),
                ),
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
    with database.connect(readonly=True) as cnx:
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


@rt("/{database:Item}/row/{table}")
def get(request, database: items.Item, table: str):
    "Add a row to the table."
    assert isinstance(database, items.Database)
    schema = database.get_schema()
    inputs = []
    for name, column in schema[table]["columns"].items():
        label = [Strong(name), " ", column["type"]]
        if not column["null"]:
            label.append(" NOT NULL")
        if column["primary"]:
            label.append(" PRIMARY KEY")
        kwargs = dict(
            name=name, required=not column["null"], autofocus=not bool(inputs)
        )
        if column["type"] == "INTEGER":
            inputs.append((Div(*label), Input(type="number", step="1", **kwargs)))
        elif column["type"] == "REAL":
            inputs.append((Div(*label), Input(type="number", **kwargs)))
        else:
            inputs.append((Div(*label), Input(type="text", **kwargs)))
    return (
        Title(f"Add row to table {table}"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li("Add row to table ", table),
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
                    f"{schema[table]['count']} rows",
                    href=f"{database.url}/rows/{table}",
                    role="button",
                    cls="thin",
                ),
                cls="grid",
            ),
            Form(
                Fieldset(*[Label(i[0], i[1]) for i in inputs]),
                Input(type="submit", value="Add row"),
                action=f"{database.url}/row/{table}",
                method="POST",
            ),
            components.get_cancel_form(database.url),
            cls="container",
        ),
    )


@rt("/{database:Item}/row/{table}")
def post(session, database: items.Item, table: str, form: dict):
    "Actually add the row to the table."
    assert isinstance(database, items.Database)
    schema = database.get_schema()
    columns = []
    values = []
    try:
        for name, column in schema[table]["columns"].items():
            columns.append(name)
            value = form.get(name)
            if column["type"] == "INTEGER":
                if value:
                    value = int(value)
                elif column["null"]:
                    value = None
                else:
                    raise ValueError(f"{name} requries a value")
            elif column["type"] == "REAL":
                if value:
                    value = float(value)
                elif column["null"]:
                    value = None
                else:
                    raise ValueError(f"{column['name']} requries a value")
            else:
                if value:
                    pass
                elif column["null"]:
                    value = None
                else:
                    value = ""
            values.append(value)
    except (TypeError, ValueError) as error:
        raise errors.Error(error)
    with database.connect() as cnx:
        cnx.execute(
            f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' * len(values))})",
            values,
        )
    add_toast(session, "Row added.", "success")
    return components.redirect(f"{database.url}/row/{table}")


@rt("/{database:Item}/rows/{relation}")
def get(database: items.Item, relation: str):
    "Display row values from table or view."
    assert isinstance(database, items.Database)
    schema = database.get_schema()
    title = f"{schema[relation]['type'].capitalize()} {relation}"
    with database.connect(readonly=True) as cnx:
        rows = cnx.execute(f"SELECT * FROM {relation}").fetchall()
    db_items = [
        Div(
            components.get_database_icon(),
            A(database.title, href=database.url),
        ),
        Div(
            Button(
                f"{schema[relation]['count']} rows",
                cls="secondary outline thin",
                style="margin-left: 1em;",
            ),
            A(
                "Add row",
                href=f"{database.url}/row/{relation}",
                role="button",
                cls="thin",
                style="margin-left: 1em;",
            ),
        ),
        Div(
            A(
                "Download CSV",
                href=f"{database.url}/csv/{relation}",
                role="button",
                cls="secondary outline thin",
            ),
            A(
                "Download JSON",
                href=f"{database.url}/json/{relation}",
                role="button",
                cls="secondary outline thin",
            ),
            cls="right",
        ),
    ]
    table_items = Tr(*[Th(name) for name in schema[relation]["columns"]])
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(title),
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
    title = "Upload CSV file"
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
                            name="table",
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
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/{database:Item}/csv")
async def post(request, database: items.Item, table: str, upfile: UploadFile):
    assert isinstance(database, items.Database)
    columns, rows = parse_csv_content(await upfile.read())
    try:
        with database.connect() as cnx:
            sql = ", ".join([c["sql"] for c in columns])
            cnx.execute(f"CREATE TABLE {table} ({sql})")
            sql = f"({', '.join([c['name'] for c in columns])}) VALUES ({', '.join(['?'] * len(columns))})"
            cnx.executemany(f"INSERT INTO {table} {sql}", rows)
    except sqlite3.Error as error:
        raise errors.Error(error)
    return components.redirect(database.url)


@rt("/{database:Item}/csv/{relation:str}")
def get(database: items.Item, relation: str):
    "Download the table or view in CSV format."
    assert isinstance(database, items.Database)
    schema = database.get_schema()
    outfile = io.StringIO()
    writer = csv.writer(outfile, quoting=csv.QUOTE_MINIMAL)
    column_names = list(schema[relation]["columns"].keys())
    writer.writerow(column_names)
    with database.connect(readonly=True) as cnx:
        writer.writerows(
            cnx.execute(f"SELECT {','.join(column_names)} FROM {relation}")
        )
    outfile.seek(0)
    content = outfile.read().encode("utf-8")
    return Response(
        headers={
            "Content-Type": f"{constants.CSV_MIMETYPE}; charset=utf-8",
            "Content-Disposition": f'attachment; filename="{database.id}_{relation}.csv"',
        },
        content=content,
        status_code=HTTP.OK,
    )


@rt("/{database:Item}/json/{relation:str}")
def get(database: items.Item, relation: str):
    "Get the table or view in JSON format."
    assert isinstance(database, items.Database)
    schema = database.get_schema()
    column_names = list(schema[relation]["columns"].keys())
    with database.connect(readonly=True) as cnx:
        rows = cnx.execute(
            f"SELECT {','.join(column_names)} FROM {relation}"
        ).fetchall()
    return {
        "$id": f"database {database.id}; {schema[relation]['type']} {relation}",
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
        with database.connect() as cnx:
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
                Span(f"{len(result)} rows", cls="center"),
                Form(
                    Input(type="hidden", name="sql", value=sql),
                    Input(
                        type="submit",
                        value="Create view",
                    ),
                    method="GET",
                    action=f"{database.url}/view",
                ),
                Form(
                    Input(type="hidden", name="sql", value=sql),
                    Input(
                        type="submit",
                        value="Download CSV",
                        cls="secondary outline",
                    ),
                    method="POST",
                    action=f"{database.url}/execute/csv",
                ),
                Form(
                    Input(type="hidden", name="sql", value=sql),
                    Input(
                        type="submit",
                        value="Download JSON",
                        cls="secondary outline",
                    ),
                    method="POST",
                    action=f"{database.url}/execute/json",
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
                        database.title,
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
                get_database_overview(database, display=True),
            ),
            Card(
                Form(
                    Fieldset(
                        Label("SQL command"),
                        Input(type="text", name="sql", value=sql or "", autofocus=True),
                    ),
                    Input(type="submit", value="Execute"),
                    action=f"{database.url}/execute",
                    method="POST",
                ),
                components.get_cancel_form(database.url),
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
    with database.connect() as cnx:
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
    with database.connect() as cnx:
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
        Title(f"Edit {database.title}"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(Strong("Edit "), database.title),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                components.get_title_input(database),
                Div(
                    Label(
                        Span(
                            "Current database: ",
                            A(database.filename, href=database.bin_url),
                        ),
                        Div(
                            Input(
                                type="file",
                                name="upfile",
                                aria_describedby="file-helper",
                            ),
                            Small(
                                "Binary Sqlite3 database file (optional).",
                                id="file-helper",
                            ),
                        ),
                    ),
                    cls="grid",
                ),
                components.get_text_input(database),
                Input(type="submit", value="Save"),
                action=f"{database.url}/edit",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
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
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/{source:Item}/copy")
def post(request, source: items.Database, title: str):
    "Actually copy the database."
    assert isinstance(source, items.Database)
    databasename = pathlib.Path(source.databasename)
    database = items.Database()
    database.owner = request.scope["auth"]
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


@rt("/{database:Item}/view")
def get(request, database: items.Item, sql: str = None):
    "Form for creating a view in the database."
    assert isinstance(database, items.Database)
    title = f"Create view in database {database.title}"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Create view in database {database.title}"),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                Fieldset(
                    Label(
                        "SQL select statement",
                        Input(
                            type="text",
                            name="sql",
                            value=sql or "",
                        ),
                    ),
                    Label(
                        "View name",
                        Input(
                            type="text",
                            name="view",
                        ),
                    ),
                ),
                Input(
                    type="submit",
                    value="Create view",
                ),
                action=f"{database.url}/view",
                method="POST",
            ),
            components.get_cancel_form(database.url),
            cls="container",
        ),
    )


@rt("/{database:Item}/view")
def post(request, database: items.Item, sql: str, view: str):
    "Actually create a view in the database."
    assert isinstance(database, items.Database)
    with database.connect() as cnx:
        cnx.execute(f"CREATE VIEW {view} AS {sql}")
    return components.redirect(database.url)


@rt("/{database:Item}/delete")
def get(request, database: items.Item):
    "Ask for confirmation to delete the database."
    assert isinstance(database, items.Database)
    redirect = urllib.parse.urlsplit(request.headers["Referer"]).path
    if redirect == database.url:
        redirect = "/databases"
    return (
        Title(f"Delete {database.title}"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(Strong("Delete "), database.title),
                ),
            ),
            cls="container",
        ),
        Main(
            H3("Really delete the database? All data will be lost."),
            Form(
                Input(
                    type="hidden",
                    name="redirect",
                    value=redirect,
                ),
                Input(
                    type="submit",
                    value="Yes, delete",
                ),
                action=f"{database.url}/delete",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
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
def get(request, database: items.Item):
    "Add a plot in the database."
    assert isinstance(database, items.Database)
    schema = database.get_schema()
    return (
        Title("Add a plot"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li("Add a plot"),
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
                        "Title",
                        Input(
                            type="text",
                            name="title",
                            required=True,
                        ),
                    )
                ),
                Fieldset(
                    Legend("Type of plot"),
                    Input(type="radio", id="xy", name="type", value="xy"),
                    Label("X/Y plot", htmlFor="xy"),
                    Input(
                        type="radio",
                        id="barchart",
                        name="type",
                        value="barchart",
                        disabled=True,
                    ),
                    Label("barchart", htmlFor="barchart"),
                    Input(
                        type="radio",
                        id="piechart",
                        name="type",
                        value="piechart",
                        disabled=True,
                    ),
                    Label("piechart", htmlFor="piechart"),
                ),
                Input(type="submit", value="Add plot"),
                action=f"{database.url}/plot",
                method="POST",
            ),
            components.get_cancel_form(database.url),
            cls="container",
        ),
    )


@rt("/{database:Item}/plot")
def post(request, database: items.Item, form: dict):
    "Actually add a plot in the database."
    assert isinstance(database, items.Database)
    if not form.get("type"):
        raise errors.Error("plot type must be provided")
    assert form["type"] == "xy", "XXX only X/Y plot implemented currently"
    title = form["title"]
    name = utils.normalize(title)
    if database.frontmatter.get("plots", {}).get(name):
        raise errors.Error(f"a plot '{name}' is already defined")
    result = dict(
        type=form["type"],
        title=title,
        description="",
        markers=[],
    )
    database.frontmatter.setdefault("plots", {})[name] = result
    database.write()
    return components.redirect(f"{database.url}/plot/{name}/edit")


@rt("/{database:Item}/plot/{plotname}")
def get(request, database: items.Item, plotname: str):
    "View the named plot in the database."
    assert isinstance(database, items.Database)
    try:
        plot = database.plots[plotname]
    except KeyError:
        raise errors.Error("no such plot", HTTP.NOT_FOUND)
    assert plot["type"] == "xy", "XXX only X/Y plot implemented currently"
    schema = database.get_schema()
    with database.connect(readonly=True) as cnx:
        kwargs = {}
        try:
            kwargs["width"] = plot["width"]
        except KeyError:
            pass
        try:
            kwargs["height"] = plot["height"]
        except KeyError:
            pass
        markers = []
        for marker in plot["markers"]:
            x_relation, x_column = marker["x"].split(" / ")
            rows = cnx.execute(f"SELECT {x_column} FROM {x_relation}").fetchall()
            x = [r[0] for r in rows]
            if schema[x_relation]["columns"][x_column]["type"] == "TEXT":
                try:
                    datetime.date.fromisoformat(x[0])
                except ValueError:
                    pass
                else:
                    x = np.array(x, dtype=np.datetime64)
                    kwargs["x_axis_type"] = "datetime"
            y_relation, y_column = marker["y"].split(" / ")
            rows = cnx.execute(f"SELECT {y_column} FROM {y_relation}").fetchall()
            y = [r[0] for r in rows]
            if schema[y_relation]["columns"][y_column]["type"] == "TEXT":
                try:
                    datetime.date.fromisoformat(y[0])
                except ValueError:
                    pass
                else:
                    y = np.array(y, dtype=np.datetime64)
                    kwargs["y_axis_type"] = "datetime"
            markers.append(dict(type=marker["type"], x=x, y=y, color=marker["color"]))
        figure = bokeh.plotting.figure(title=plot["title"], **kwargs)
        for marker in markers:
            match marker["type"]:
                case "line":
                    figure.line(marker["x"], marker["y"], color=marker["color"])
                case "scatter":
                    figure.scatter(marker["x"], marker["y"], color=marker["color"])
                case _:
                    raise NotImplementedError
        script, div = bokeh.embed.components(figure)
    if descr := plot.get("description"):
        decription = Card(NotStr(marko.convert(descr)))
    else:
        description = Card(I("No description."))
    return (
        Title(plot["title"]),
        Script(src="/clipboard.min.js"),
        NotStr(bokeh.resources.CDN.render()),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(Strong(plot["title"])),
                    Li(
                        A(
                            components.get_icon("pencil.svg", title=f"Edit {plotname}"),
                            href=f"{database.url}/plot/{plotname}/edit",
                        ),
                        A(
                            components.get_icon("copy.svg", title=f"Copy {plotname}"),
                            href=f"{database.url}/plot/{plotname}/copy",
                        ),
                        A(
                            components.get_icon(
                                "trash.svg", title=f"Delete {plotname}"
                            ),
                            href=f"{database.url}/plot/{plotname}/delete",
                        ),
                    ),
                ),
                Ul(Li(components.search_form())),
            ),
            cls="container",
        ),
        Main(
            Card(
                components.get_database_icon(),
                A(database.title, href=database.url),
            ),
            Card(NotStr(div)),
            description,
            cls="container",
        ),
        Script("new ClipboardJS('.to_clipboard');", type="text/javascript"),
        NotStr(script),
    )


@rt("/{database:Item}/plot/{plotname}/edit")
def get(request, database: items.Item, plotname: str):
    "Edit the named plot in the database."
    assert isinstance(database, items.Database)
    schema = database.get_schema()
    plot = database.plots[plotname]
    sources = []
    for name, relation in schema.items():
        for column in relation["columns"]:
            sources.append(f"{name} / {column}")
    return (
        Title(f"Edit {plot['title']}"),
        Script(src="/clipboard.min.js"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(Strong("Edit "), plotname),
                ),
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
                            value=plot["title"],
                            required=True,
                        ),
                    ),
                    Label(
                        "Description",
                        Textarea(plot["description"] or "", name="description"),
                    ),
                ),
                Fieldset(
                    Label(
                        "Width",
                        Input(
                            type="number",
                            name="width",
                            min="1",
                            step="1",
                            value=f"{plot.get('width') or ''}",
                        ),
                    ),
                    Label(
                        "Height",
                        Input(
                            type="number",
                            name="height",
                            min="1",
                            step="1",
                            value=f"{plot.get('height') or ''}",
                        ),
                    ),
                    cls="grid",
                ),
                Fieldset(
                    Label(
                        "Markers",
                        Table(
                            Thead(
                                Tr(
                                    Th("Type"),
                                    Th("X source"),
                                    Th("Y source"),
                                    Th("Color", colspan=2),
                                    Th("Delete"),
                                ),
                            ),
                            Tbody(
                                *[
                                    Tr(
                                        Td(marker["type"].capitalize()),
                                        Td(marker["x"]),
                                        Td(marker["y"]),
                                        Td(
                                            Input(
                                                type="text",
                                                name=f"color_text_{pos}",
                                                value=utils.to_name_color(
                                                    marker.get("color") or ""
                                                ),
                                            ),
                                        ),
                                        Td(
                                            Input(
                                                type="color",
                                                name=f"color_palette_{pos}",
                                                value=utils.to_hex_color(marker.get("color")),
                                                style="width: 4em;",
                                            ),
                                        ),
                                        Td(
                                            Input(
                                                type="checkbox",
                                                name="delete",
                                                value=str(pos),
                                            )
                                        ),
                                    )
                                    for pos, marker in enumerate(plot["markers"])
                                ]
                            ),
                        ),
                    )
                ),
                Fieldset(
                    Label(
                        "Add marker",
                        Div(
                            Select(
                                Option("Type of marker", selected=True, disabled=True),
                                Option("Scatter", value="scatter"),
                                Option("Line", value="line"),
                                name="type",
                            ),
                            Select(
                                Option("X source", selected=True, disabled=True),
                                *[Option(s) for s in sources],
                                name="x",
                            ),
                            Select(
                                Option("Y source", selected=True, disabled=True),
                                *[Option(s) for s in sources],
                                name="y",
                            ),
                            Input(
                                type="text",
                                name="color_text",
                                placeholder="Color name",
                            ),
                            Input(
                                type="color",
                                name="color_palette",
                                style="width: 4em;",
                            ),
                            cls="grid",
                        ),
                    ),
                ),
                Input(type="submit", value="Save"),
                action=f"{database.url}/plot/{plotname}/edit",
                method="POST",
            ),
            components.get_cancel_form(f"{database.url}/plot/{plotname}"),
            cls="container",
        ),
    )


@rt("/{database:Item}/plot/{plotname}/edit")
def post(request, database: items.Item, plotname: str, form: dict):
    "Actually edit the named plot in the database."
    assert isinstance(database, items.Database)
    schema = database.get_schema()
    plot = database.plots[plotname]
    plot["title"] = form["title"]
    plot["description"] = form.get("description") or ""
    try:
        plot["width"] = int(form.get("width"))
    except (TypeError, ValueError):
        plot.pop("width", None)
    try:
        plot["height"] = int(form.get("height"))
    except (TypeError, ValueError):
        plot.pop("height", None)

    # Delete markers.
    delete = form.get("delete") or []
    if delete and isinstance(delete, str):
        delete = [delete]
    for pos in delete:
        plot["markers"][int(pos)] = None

    # Modify remaining markers.
    for pos, marker in enumerate(plot["markers"]):
        if marker is None:
            continue
        marker["color"] = (
            form.get(f"color_text_{pos}") or form.get(f"color_palette_{pos}") or "black"
        )

    # Add new marker.
    if type := form.get("type"):
        color = form.get("color_text") or form.get("color_palette") or "black"
        if not (x := form.get("x")):
            raise errors.Error("no X source given")
        if not (y := form.get("y")):
            raise errors.Error("no Y source given")
        plot["markers"].append(dict(type=type, x=x, y=y, color=color))

    # Remove deleted markers.
    plot["markers"] = [m for m in plot["markers"] if m]
    database.write()
    return components.redirect(f"{database.url}/plot/{plotname}")


@rt("/{database:Item}/plot/{plotname}/copy")
def get(request, database: items.Item, plotname: str):
    "Copy the named plot in the database."
    assert isinstance(database, items.Database)
    return (
        Title(f"Copy {plotname}"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(Strong("Copy "), plotname),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                Fieldset(
                    Label(
                        "Plot title",
                        Input(
                            type="text",
                            name="title",
                            value=f"Copy of {database.plots[plotname]['title']}",
                            required=True,
                        ),
                    ),
                ),
                Input(
                    type="submit",
                    value="Copy",
                ),
                action=f"{database.url}/plot/{plotname}/copy",
                method="POST",
            ),
            components.get_cancel_form(f"{database.url}/plot/{plotname}"),
            cls="container",
        ),
    )


@rt("/{database:Item}/plot/{plotname}/copy")
def post(request, database: items.Item, plotname: str, form: dict):
    "Actually copy the named plot in the database."
    assert isinstance(database, items.Database)
    name = utils.normalize(form["title"])
    if name in database.frontmatter["plots"]:
        raise errors.Error(f"a plot '{name}' is already defined")
    plot = copy.deepcopy(database.frontmatter["plots"][plotname])
    plot["title"] = form["title"]
    database.frontmatter["plots"][name] = plot
    database.write()
    return components.redirect(f"{database.url}/plot/{name}")


@rt("/{database:Item}/plot/{plotname}/delete")
def get(request, database: items.Item, plotname: str):
    "Ask for confirmation to delete the plot."
    assert isinstance(database, items.Database)
    return (
        Title(f"Delete {plotname}"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(Strong("Delete "), plotname),
                ),
            ),
            cls="container",
        ),
        Main(
            H3("Really delete the plot? All data will be lost."),
            Form(
                Input(
                    type="submit",
                    value="Yes, delete",
                ),
                action=f"{database.url}/plot/{plotname}/delete",
                method="POST",
            ),
            components.get_cancel_form(f"{database.url}/plot/{plotname}"),
            cls="container",
        ),
    )


@rt("/{database:Item}/plot/{plotname}/delete")
def post(database: items.Item, plotname: str):
    "Actually delete the database."
    assert isinstance(database, items.Database)
    database.frontmatter.get("plots", {}).pop(plotname, None)
    if not database.plots:
        database.frontmatter.pop("plots", None)
    database.write()
    return components.redirect(database.url)


def get_database_overview(database, display=False):
    "Get an overview of the basic structure of the database."
    rows = []
    for name, item in database.get_schema().items():
        spec = [
            Li(
                f"{column_name} {column['type']} {not column['null'] and 'NOT NULL' or ''} {column['primary'] and 'PRIMARY KEY' or ''}"
            )
            for column_name, column in item["columns"].items()
        ]
        spec.append(Li(item["sql"]))
        if item["type"] == "table":
            add_row_button = A(
                "Add row",
                href=f"{database.url}/row/{name}",
                role="button",
                cls="thin",
            )
        else:
            add_row_button = ""

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
                        open=display,
                    ),
                ),
                Td(
                    A(
                        f"{item['count']} rows",
                        href=f"{database.url}/rows/{name}",
                        role="button",
                        cls="thin",
                    ),
                    add_row_button,
                    cls="top",
                ),
                Td(
                    A(
                        "Download CSV",
                        href=f"{database.url}/csv/{name}",
                        role="button",
                        cls="secondary outline thin",
                    ),
                    A(
                        "Download JSON",
                        href=f"{database.url}/json/{name}",
                        role="button",
                        cls="secondary outline thin",
                    ),
                    cls="right top",
                ),
            ),
        )
    return Table(Tbody(*rows))


def parse_csv_content(content):
    """Read the CSV content and figure out the SQL for the corresponding table.
    Return tuple (columns, rows) where 'columns' is the definition and 'rows' the data.
    """
    reader = csv.reader(io.StringIO(content.decode("utf-8")))
    header = next(reader)
    rows = list(reader)
    columns = []
    for pos, name in enumerate(header):
        column = dict(name=name, type="INTEGER", null=False)
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
    return columns, rows
