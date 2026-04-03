"Database item page."

import contextlib
import copy
import csv
import datetime
from http import HTTPStatus as HTTP
import io
import json
import os
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
def get():
    "Form for adding a database."
    title = "Add database"
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
                Label(
                    "Optional Sqlite3 database binary file.",
                    Input(
                        type="file",
                        name="upfile",
                        aria_describedby="file-helper",
                    ),
                ),
                components.get_text_input(),
                components.get_tags_input(),
                Input(type="submit", value="Add database"),
                action="/database/",
                method="POST",
            ),
            components.get_cancel_form("/"),
            cls="container",
        ),
    )


@rt("/")
async def post(
    title: str, text: str, upfile: UploadFile = None, tags: list[str] = None
):
    "Actually create the database."
    database = items.Database()
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
    database.tags = tags
    database.write()
    return components.redirect(database.url)


@rt("/{database:Item}")
def get(database: items.Item, page: int = 1, tags_page: int = 1, refs_page: int = 1):
    "View the data and the list of plots for the database."
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
        )
        for name, plot in database.plots.items()
    ]

    return (
        Title(database.title),
        components.clipboard_script(),
        components.get_header_item_view(database),
        Main(
            components.get_text_card(database),
            get_overview(database),
            Card(
                Form(
                    Input(type="submit", value="SQL command", cls="outline"),
                    action=f"{database.url}/execute",
                    method="POST",
                ),
                Details(
                    Summary("Operations..."),
                    Ul(
                        Li(A("Add plot", href=f"{database.url}/plot")),
                        Li(A("Create table from CSV file", href=f"{database.url}.csv")),
                        Li(A("Download Sqlite", href=database.url_file)),
                        Li(A("Download SQL", href=database.url_sql)),
                    ),
                    cls="dropdown",
                ),
                cls="grid",
            ),
            Card(
                Header("Plots"),
                (
                    Table(
                        Thead(
                            Tr(
                                Th("Plot"),
                                Th("Type"),
                                Th(),
                            ),
                        ),
                        Tbody(*plot_rows),
                    )
                    if plot_rows
                    else I("No plots.")
                ),
            ),
            Form(
                components.get_tags_card(database, tags_page),
                components.get_refs_card(database, refs_page),
                action=database.url,
            ),
            cls="container",
        ),
        components.get_footer_item_view(
            database, size=f"{database.size:,d} + {database.file_size:,d} bytes"
        ),
        components.clipboard_activate(),
    )


@rt("/{database:Item}{ext:Ext}")
def get(database: items.Item, ext: str):
    "Download the content of the database in Sqlite or SQL format."
    assert isinstance(database, items.Database)
    match ext:
        case ".sqlite":
            return FileResponse(database.filepath)
        case ".sql":
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
        case _:
            raise errors.Error("no such database", HTTP.NOT_FOUND)


@rt("/{database:Item}/row/{tablename:str}")
def get(database: items.Item, tablename: str):
    "Add a row to the table."
    assert isinstance(database, items.Database)
    schema = database.get_schema()
    inputs = []
    for name, column in schema[tablename]["columns"].items():
        label = [Strong(name), " ", column["type"]]
        if not column["null"]:
            label.append(" NOT NULL")
        if column["primary"]:
            label.append(" PRIMARY KEY")
        kwargs = dict(name=name, required=not column["null"])
        if column["type"] == "INTEGER":
            inputs.append((Div(*label), Input(type="number", step="1", **kwargs)))
        elif column["type"] == "REAL":
            inputs.append((Div(*label), Input(type="number", **kwargs)))
        else:
            inputs.append((Div(*label), Input(type="text", **kwargs)))
    title = "Add row to table"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(database)),
                    Li(title),
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
                    "Table ",
                    Strong(tablename),
                    f", {schema[tablename]['count']} rows",
                    href=f"{database.url}/rows/{tablename}",
                    role="button",
                    cls="outline",
                ),
                cls="grid",
            ),
            Form(
                *[Label(i[0], i[1]) for i in inputs],
                Input(type="submit", value="Add row"),
                action=f"{database.url}/row/{tablename}",
                method="POST",
            ),
            components.get_cancel_form(database.url),
            cls="container",
        ),
    )


@rt("/{database:Item}/row/{tablename:str}")
def post(session, database: items.Item, tablename: str, form: dict):
    "Actually add the row to the table."
    assert isinstance(database, items.Database)
    schema = database.get_schema()
    columns = []
    row = []
    try:
        for name, column in schema[tablename]["columns"].items():
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
            row.append(value)
    except (TypeError, ValueError) as error:
        raise errors.Error(error)
    with set_modified_when_changed(database):
        with database.connect() as cnx:
            columns = ",".join(columns)
            values = ",".join("?" * len(row))
            sql = f"INSERT INTO {tablename} ({columns}) VALUES ({values})"
            cnx.execute(sql, row)
    add_toast(session, "Row added.", "success")
    return components.redirect(f"{database.url}/row/{tablename}")


@rt("/{database:Item}/rows/{relname:Name}")
def get(database: items.Item, relname: str):
    "Display table or view rows."
    assert isinstance(database, items.Database)
    schema = database.get_schema()
    title = f"{schema[relname]['type'].capitalize()} {relname}"
    # column_headers = Tr(*[Th(name) for name in schema[relname]["columns"]])
    return (
        Title(title),
        components.tabulator_style(),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(database)),
                    Li(title),
                ),
            ),
            cls="container",
        ),
        Main(
            Card(
                Header(
                    Div(
                        components.get_database_icon(),
                        A(database.title, href=database.url),
                    ),
                    Strong(f"{schema[relname]['count']} rows"),
                    cls="grid",
                ),
                Div(id="table"),
            ),
            cls="container",
        ),
        Footer(
            Hr(),
            Div(
                Div(database.modified_local),
                Div(f"{database.size:,d} + {database.file_size:,d} bytes"),
                cls="grid",
            ),
            cls="container",
        ),
        components.tabulator_lib(),
        Script(
            f"""var table = new Tabulator("#table", {{
height: 500,
autoColumns: true,
ajaxURL: "{database.url}/rows/{relname}.json",
ajaxResponse: function(url, params, response) {{return response.data}},
}});""",
            type="text/javascript",
        ),
    )


@rt("/{database:Item}/rows/{relname:Name}{ext:Ext}")
def get(database: items.Item, relname: str, ext: str):
    "Download the table or view rows in CSV or JSON format."
    assert isinstance(database, items.Database)
    schema = database.get_schema()
    columns = list(schema[relname]["columns"].keys())
    match ext:
        case ".csv":
            outfile = io.StringIO()
            writer = csv.writer(outfile, quoting=csv.QUOTE_MINIMAL)
            writer.writerow(columns)
            with database.connect(readonly=True) as cnx:
                sql = f"SELECT {','.join(columns)} FROM {relname}"
                writer.writerows(cnx.execute(sql))
            outfile.seek(0)
            content = outfile.read().encode("utf-8")
            return Response(
                headers={
                    "Content-Type": f"{constants.CSV_MIMETYPE}; charset=utf-8",
                    "Content-Disposition": f'attachment; filename="{database.id}_{relname}.csv"',
                },
                content=content,
                status_code=HTTP.OK,
            )
        case ".json":
            with database.connect(readonly=True) as cnx:
                sql = f"SELECT {','.join(columns)} FROM {relname}"
                rows = cnx.execute(sql).fetchall()
            return {
                "$id": f"database {database.id}; {schema[relname]['type']} {relname}",
                "data": [dict(zip(columns, row)) for row in rows],
            }
        case _:
            raise errors.Error("invalid format", HTTP.NOT_FOUND)


@rt("/{database:Item}/rows/{tablename:str}/csv")
def get(database: items.Item, tablename: str):
    "Add data to the table from a CSV file."
    assert isinstance(database, items.Database)
    schema = database.get_schema()
    title = f"Add CSV file to table {tablename}"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(databse)),
                    Li(title),
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
                    f"{schema[tablename]['count']} rows",
                    href=f"{database.url}/rows/{tablename}",
                    role="button",
                    cls="thin",
                ),
                cls="grid",
            ),
            Form(
                Label(
                    "CSV file to upload.",
                    Input(
                        type="file",
                        name="upfile",
                        aria_describedby="file-helper",
                    ),
                    Small(
                        "Header and content must match the table definition.",
                        id="file-helper",
                    ),
                ),
                Input(type="submit", value="Add CSV file"),
                action=f"{database.url}/rows/{tablename}/csv",
                method="POST",
            ),
            components.get_cancel_form(database.url),
            cls="container",
        ),
    )


@rt("/{database:Item}/rows/{tablename:str}/csv")
async def post(database: items.Item, tablename: str, upfile: UploadFile):
    "Actually add data to the table from a CSV file."
    assert isinstance(database, items.Database)
    table_columns = database.get_schema()[tablename]["columns"]
    required_table_columns = dict(
        [(n, c) for n, c in table_columns.items() if not c["null"]]
    )
    csv_columns, rows = parse_csv_content(await upfile.read())
    csv_column_names = [c["name"] for c in csv_columns]
    csv_data = [dict(zip(csv_column_names, row)) for row in rows]
    csv_columns = dict([(c["name"], c) for c in csv_columns])
    used_columns = list(set(table_columns.keys()).intersection(csv_column_names))
    try:
        for name, column in required_table_columns.items():
            if name not in csv_columns:
                raise KeyError(f"missing column {name} in CSV file")
            if csv_columns[name]["null"]:
                raise ValueError(
                    f"column {name} in CSV file contains disallowed NULL value"
                )
            if column["type"] == "TEXT":
                for data in csv_data:
                    if not data[name]:
                        raise ValueError(
                            f"column {name} in CSV file contains disallowed empty string value"
                        )
        for name in used_columns:
            if table_columns[name]["type"] != csv_columns[name]["type"]:
                raise ValueError(f"wrong type for column {name}")
        rows = [[data[n] for n in used_columns] for data in csv_data]
        with set_modified_when_changed(database):
            with database.connect() as cnx:
                columns = ",".join(used_columns)
                values = ",".join(["?"] * len(used_columns))
                sql = f"INSERT INTO {tablename} ({columns}) VALUES ({values})"
                cnx.executemany(sql, rows)
    except (KeyError, ValueError) as error:
        raise errors.Error(error)
    return components.redirect(database.url)


@rt("/{database:Item}/csv")
def get(request, database: items.Item):
    "Create table from CSV file upload."
    assert isinstance(database, items.Database)
    title = "Upload CSV file"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(database)),
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
                Label(
                    "Table name",
                    Input(
                        type="text",
                        name="tablename",
                        required=True,
                    ),
                ),
                Label(
                    "CSV file to upload.",
                    Input(
                        type="file",
                        name="upfile",
                        aria_describedby="file-helper",
                    ),
                    Small(
                        "Must contain a header. The table definition is inferred from the content.",
                        id="file-helper",
                    ),
                ),
                Input(type="submit", value="Upload"),
                action=f"{database.url}/csv",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/{database:Item}/csv")
async def post(database: items.Item, tablename: str, upfile: UploadFile):
    """Actually create table from CSV file upload.
    Determine columns from header and data.
    """
    assert isinstance(database, items.Database)
    columns, rows = parse_csv_content(await upfile.read())
    try:
        with set_modified_when_changed(database):
            with database.connect() as cnx:
                sql = ", ".join([c["sql"] for c in columns])
                cnx.execute(f"CREATE TABLE {tablename} ({sql})")
                columns = ",".join([c["name"] for c in columns])
                values = ",".join(["?"] * len(columns))
                sql = f"INSERT INTO {tablename} ({columns}) VALUES ({values})"
                cnx.executemany(sql, rows)
    except sqlite3.Error as error:
        raise errors.Error(error)
    return components.redirect(database.url)


@rt("/{database:Item}/execute")
def post(database: items.Item, sql: str = None):
    "Execute a SQL command."
    assert isinstance(database, items.Database)
    column_names = []
    result = []
    error_card = ""
    if sql:
        with set_modified_when_changed(database):
            with database.connect() as cnx:
                try:
                    cursor = cnx.execute(sql)
                except sqlite3.Error as error:
                    error_card = Card(
                        Header("Error", style="color: red;"), Pre(str(error))
                    )
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
                    Input(type="submit", value="Create view"),
                    action=f"{database.url}/view",
                ),
                Form(
                    Input(type="hidden", name="sql", value=sql),
                    Input(type="submit", value="Download CSV", cls="secondary outline"),
                    method="POST",
                    action=f"{database.url}/execute.csv",
                ),
                Form(
                    Input(type="hidden", name="sql", value=sql),
                    Input(
                        type="submit", value="Download JSON", cls="secondary outline"
                    ),
                    method="POST",
                    action=f"{database.url}/execute.json",
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
    title = "SQL command"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(database)),
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
            get_overview(database, display=True),
            Card(
                Form(
                    Label("SQL command"),
                    Input(type="text", name="sql", value=sql or ""),
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


@rt("/{database:Item}/execute{ext:Ext}")
def post(database: items.Item, sql: str, ext: str):
    "Execute a SQL command and download the result as CSV or JSON."
    assert isinstance(database, items.Database)
    assert sql
    with set_modified_when_changed(database):
        with database.connect() as cnx:
            try:
                cursor = cnx.execute(sql)
            except sqlite3.Error as error:
                errors.Error(str(error))
            else:
                header = [t[0] for t in cursor.description]
                rows = cursor.fetchall()
    match ext:
        case ".csv":
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
        case ".json":
            return {
                "$id": f"database {database.id}",
                "query": sql,
                "data": [dict(zip(header, row)) for row in rows],
            }
        case _:
            raise errors.Error("invalid format", HTTP.NOT_FOUND)


@rt("/{database:Item}/edit")
def get(request, database: items.Item):
    "Form for editing the data for the database."
    assert isinstance(database, items.Database)
    return (
        *components.get_header_item_edit(database),
        Main(
            Form(
                components.get_title_input(database.title),
                components.get_text_input(database.text),
                components.get_tags_input(database.tags),
                Input(type="submit", value="Save"),
                action=f"{database.url}/edit",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/{database:Item}/edit")
async def post(database: items.Item, title: str, text: str, tags: list[str] = None):
    "Actually edit the database."
    assert isinstance(database, items.Database)
    database.title = title.strip()
    database.text = text.strip()
    database.tags = tags
    database.write()
    return components.redirect(database.url)


@rt("/{database:Item}/copy")
def get(request, database: items.Item):
    "Form for making a copy of the database."
    assert isinstance(database, items.Database)
    title = f"Copy '{database.title}'"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(database)),
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
                    value=database.title,
                    placeholder="Title...",
                    required=True,
                ),
                Input(type="submit", value="Copy database"),
                action=f"{database.url}/copy",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/{source:Item}/copy")
def post(source: items.Database, title: str):
    "Actually copy the database."
    assert isinstance(source, items.Database)
    databasename = pathlib.Path(source.databasename)
    database = items.Database()
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
    database.write()
    return components.redirect(database.url)


@rt("/{database:Item}/view")
def get(database: items.Item, sql: str = None):
    "Form for creating a view in the database."
    assert isinstance(database, items.Database)
    title = f"Create view in '{database.title}'"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(database)),
                    Li(title),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
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
                Input(type="submit", value="Create view"),
                action=f"{database.url}/view",
                method="POST",
            ),
            components.get_cancel_form(database.url),
            cls="container",
        ),
    )


@rt("/{database:Item}/view")
def post(database: items.Item, sql: str, view: str):
    "Actually create a view in the database."
    assert isinstance(database, items.Database)
    with set_modified_when_changed(database):
        with database.connect() as cnx:
            cnx.execute(f"CREATE VIEW {view} AS {sql}")
    return components.redirect(database.url)


@rt("/{database:Item}/delete")
def get(request, database: items.Item):
    "Ask for confirmation to delete the database."
    assert isinstance(database, items.Database)
    redirect = urllib.parse.urlsplit(request.headers["Referer"]).path
    if redirect == database.url:
        redirect = "/"
    title = f"Delete '{database.title}'"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(database)),
                    Li(title),
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
                Input(type="submit", value="Yes, delete"),
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
def get(database: items.Item):
    "Add a plot in the database."
    assert isinstance(database, items.Database)
    schema = database.get_schema()
    title = f"Add a plot in '{database.title}'"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(database)),
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
                Label(
                    "Title",
                    Input(
                        type="text",
                        name="title",
                        required=True,
                    ),
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
def post(database: items.Item, form: dict):
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


@rt("/{database:Item}/plot/{plotname:str}")
def get(database: items.Item, plotname: str):
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
            x_relname, x_colname = marker["x"].split(" / ")
            rows = cnx.execute(f"SELECT {x_colname} FROM {x_relname}").fetchall()
            x = [r[0] for r in rows]
            if schema[x_relname]["columns"][x_colname]["type"] == "TEXT":
                try:
                    datetime.date.fromisoformat(x[0])
                except ValueError:
                    pass
                else:
                    x = np.array(x, dtype=np.datetime64)
                    kwargs["x_axis_type"] = "datetime"
            y_relname, y_colname = marker["y"].split(" / ")
            rows = cnx.execute(f"SELECT {y_colname} FROM {y_relname}").fetchall()
            y = [r[0] for r in rows]
            if schema[y_relname]["columns"][y_colname]["type"] == "TEXT":
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
        NotStr(bokeh.resources.CDN.render()),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(database)),
                    Li(plot["title"]),
                ),
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
            Card(
                Details(
                    Summary("Operations"),
                    Ul(
                        Li(A("Edit", href=f"{database.url}/plot/{plotname}/edit")),
                        Li(A("Copy", href=f"{database.url}/plot/{plotname}/copy")),
                        Li(A("Delete", href=f"{database.url}/plot/{plotname}/delete")),
                    ),
                    cls="dropdown",
                ),
            ),
            cls="container",
        ),
        NotStr(script),
    )


@rt("/{database:Item}/plot/{plotname:str}/edit")
def get(database: items.Item, plotname: str):
    "Edit the named plot in the database."
    assert isinstance(database, items.Database)
    schema = database.get_schema()
    plot = database.plots[plotname]
    sources = []
    for relname, relation in schema.items():
        for column in relation["columns"]:
            sources.append(f"{relname} / {column}")
    title = f"Edit '{plot['title']}'"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(database)),
                    Li(title),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
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
                                                value=utils.to_hex_color(
                                                    marker.get("color")
                                                ),
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


@rt("/{database:Item}/plot/{plotname:str}/edit")
def post(database: items.Item, plotname: str, form: dict):
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


@rt("/{database:Item}/plot/{plotname:str}/copy")
def get(database: items.Item, plotname: str):
    "Copy the named plot in the database."
    assert isinstance(database, items.Database)
    title = f"Copy '{plotname}'"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(database)),
                    Li(title),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                Label(
                    "Plot title",
                    Input(
                        type="text",
                        name="title",
                        value=f"Copy of {database.plots[plotname]['title']}",
                        required=True,
                    ),
                ),
                Input(type="submit", value="Copy"),
                action=f"{database.url}/plot/{plotname}/copy",
                method="POST",
            ),
            components.get_cancel_form(f"{database.url}/plot/{plotname}"),
            cls="container",
        ),
    )


@rt("/{database:Item}/plot/{plotname:str}/copy")
def post(database: items.Item, plotname: str, form: dict):
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


@rt("/{database:Item}/plot/{plotname:str}/delete")
def get(database: items.Item, plotname: str):
    "Ask for confirmation to delete the plot."
    assert isinstance(database, items.Database)
    title = f"Delete '{plotname}'"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(database)),
                    Li(title),
                ),
            ),
            cls="container",
        ),
        Main(
            H3("Really delete the plot? All data will be lost."),
            Form(
                Input(type="submit", value="Yes, delete"),
                action=f"{database.url}/plot/{plotname}/delete",
                method="POST",
            ),
            components.get_cancel_form(f"{database.url}/plot/{plotname}"),
            cls="container",
        ),
    )


@rt("/{database:Item}/plot/{plotname:str}/delete")
def post(database: items.Item, plotname: str):
    "Actually delete the database."
    assert isinstance(database, items.Database)
    database.frontmatter.get("plots", {}).pop(plotname, None)
    if not database.plots:
        database.frontmatter.pop("plots", None)
    database.write()
    return components.redirect(database.url)


def get_overview(database, display=False):
    "Get an overview of the basic structure of the database."
    rows = []
    for relname, relation in database.get_schema().items():
        spec = [
            Li(
                f"{column_name} {column['type']} {not column['null'] and 'NOT NULL' or ''} {column['primary'] and 'PRIMARY KEY' or ''}"
            )
            for column_name, column in relation["columns"].items()
        ]
        spec.append(Li(relation["sql"]))
        operations = []
        if relation["type"] == "table":
            operations.append(Li(A("Add row", href=f"{database.url}/row/{relname}")))
            operations.append(
                Li(A("Add CSV file", href=f"{database.url}/rows/{relname}/csv"))
            )
        operations.append(
            Li(A("Download CSV", href=f"{database.url}/rows/{relname}.csv"))
        )
        operations.append(
            Li(A("Download JSON", href=f"{database.url}/rows/{relname}.json"))
        )
        rows.append(
            Div(
                Details(
                    Summary(
                        f"{relation['type'].capitalize()} ",
                        Strong(relname),
                        role="button",
                        cls="outline",
                    ),
                    Ul(*spec),
                    open=display,
                ),
                Div(
                    Form(
                        Input(
                            type="submit",
                            value=f"{relation['count']} rows",
                            cls="outline",
                        ),
                        action=f"{database.url}/rows/{relname}",
                    ),
                    Details(
                        Summary("Operations..."),
                        Ul(*operations),
                        cls="dropdown",
                    ),
                    cls="grid",
                ),
                cls="grid",
            )
        )
    return Card(*rows)


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


@contextlib.contextmanager
def set_modified_when_changed(database):
    "Set the modified timestamp of the item if the database file changes."
    before = database.filepath.stat().st_mtime
    try:
        yield database
    finally:
        after = database.filepath.stat().st_mtime
        if after != before:
            os.utime(database.path, (database.path.stat().st_atime, after))
