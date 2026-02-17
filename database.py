"Database item page."

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
    "View the metadata and plots for the database."
    assert isinstance(database, items.Database)
    timer = Timer()
    if database.plots:
        cdn = bokeh.resources.CDN.render()
        scripts = []
        plots = []
        for title, plot in database.plots.items():
            with database as cnx:
                rows = cnx.execute(
                    f"SELECT {plot['x']}, {plot['y']} FROM {plot['tableview']}"
                ).fetchall()
                x = [r[0] for r in rows]
                y = [r[1] for r in rows]
            info = database.get_tableview_info(plot["tableview"])
            columns = dict([(c["name"], c["type"]) for c in info["columns"]])
            if columns[plot["x"]] == "TEXT":
                try:
                    datetime.date.fromisoformat(x[0])
                except ValueError:
                    pass
                else:
                    x = np.array(x, dtype=np.datetime64)
            if columns[plot["y"]] == "TEXT":
                try:
                    datetime.date.fromisoformat(y[0])
                except ValueError:
                    pass
                else:
                    y = np.array(y, dtype=np.datetime64)
            p = bokeh.plotting.figure(
                title=title, x_axis_label=plot["x"], y_axis_label=plot["y"]
            )
            match plot["type"]:
                case "line":
                    p.line(x, y)
                case "scatter":
                    p.scatter(x, y)
                case _:
                    raise NotImplementedError
            script, div = bokeh.embed.components(p)
            plots.append((div, plot))
            scripts.append(script)
        plots_table = Table(
            Tbody(
                *[
                    Tr(
                        Td(NotStr(d)),
                        Td(
                            A(
                                "Edit",
                                role="button",
                                href=f"{database.url}/plot/{p['tableview']}/{p['name']}",
                            )
                        ),
                    )
                    for d, p in plots
                ]
            )
        )
    else:
        cdn = ""
        scripts = []
        plots_table = I("None.")
    ic(str(timer))
    return (
        Title(database.title),
        Script(src="/clipboard.min.js"),
        NotStr(cdn),
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
            Card(get_database_overview(database, add_plot=True)),
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
        NotStr("\n".join(scripts)),
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


@rt("/{database:Item}/row/{table}")
def get(session, request, database: items.Item, table: str):
    "Add a row to the table."
    assert isinstance(database, items.Database)
    info = database.get_tableview_info(table)
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
        Title(f"Add row to table {table}"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li("Add row to table ", Strong(table)),
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
            Form(
                Input(
                    type="submit",
                    value="Cancel",
                    cls="secondary",
                ),
                action=database.url,
                method="GET",
            ),
            cls="container",
        ),
    )


@rt("/{database:Item}/row/{table}")
def post(session, database: items.Item, table: str, form: dict):
    "Actually add the row to the table."
    assert isinstance(database, items.Database)
    info = database.get_tableview_info(table)
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
            f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' * len(values))})",
            values,
        )
    add_toast(session, "Row added.", "success")
    return components.redirect(f"{database.url}/row/{table}")


@rt("/{database:Item}/rows/{tableview}")
def get(database: items.Item, tableview: str):
    "Display row values from table or view."
    assert isinstance(database, items.Database)
    info = database.get_tableview_info(tableview)
    title = f"{info['type'].capitalize()} {tableview}"
    with database as cnx:
        rows = cnx.execute(f"SELECT * FROM {tableview}").fetchall()
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
                href=f"{database.url}/row/{tableview}",
                role="button",
                cls="thin",
                style="margin-left: 1em;",
            ),
        ),
        Div(
            A(
                "Download CSV",
                href=f"{database.url}/csv/{tableview}",
                role="button",
                cls="secondary outline thin",
            ),
            A(
                "Download JSON",
                href=f"{database.url}/json/{tableview}",
                role="button",
                cls="secondary outline thin",
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
async def post(request, database: items.Item, table: str, upfile: UploadFile):
    assert isinstance(database, items.Database)
    content = await upfile.read()
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
    try:
        with database as cnx:
            sql = ", ".join([c["sql"] for c in columns])
            cnx.execute(f"CREATE TABLE {table} ({sql})")
            sql = f"({', '.join([c['name'] for c in columns])}) VALUES ({', '.join(['?'] * len(columns))})"
            cnx.executemany(f"INSERT INTO {table} {sql}", rows)
    except sqlite3.Error as error:
        raise errors.Error(error)
    return components.redirect(database.url)


@rt("/{database:Item}/csv/{tableview:str}")
def get(database: items.Item, tableview: str):
    "Download the table or view in CSV format."
    assert isinstance(database, items.Database)
    info = database.get_tableview_info(tableview)
    outfile = io.StringIO()
    writer = csv.writer(outfile, quoting=csv.QUOTE_MINIMAL)
    column_names = [column["name"] for column in info["columns"]]
    writer.writerow(column_names)
    with database as cnx:
        writer.writerows(
            cnx.execute(f"SELECT {','.join(column_names)} FROM {tableview}")
        )
    outfile.seek(0)
    content = outfile.read().encode("utf-8")
    return Response(
        headers={
            "Content-Type": f"{constants.CSV_MIMETYPE}; charset=utf-8",
            "Content-Disposition": f'attachment; filename="{database.id}_{tableview}.csv"',
        },
        content=content,
        status_code=HTTP.OK,
    )


@rt("/{database:Item}/json/{tableview:str}")
def get(database: items.Item, tableview: str):
    "Get the table or view in JSON format."
    assert isinstance(database, items.Database)
    info = database.get_tableview_info(tableview)
    column_names = [column["name"] for column in info["columns"]]
    with database as cnx:
        rows = cnx.execute(
            f"SELECT {','.join(column_names)} FROM {tableview}"
        ).fetchall()
    return {
        "$id": f"database {database.id}; {info['type']} {tableview}",
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
                Form(
                    Input(
                        type="submit",
                        value="Cancel",
                        cls="secondary",
                    ),
                    action=database.url,
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
            Form(
                Input(
                    type="submit",
                    value="Cancel",
                    cls="secondary",
                ),
                action=database.url,
                method="GET",
            ),
            cls="container",
        ),
    )


@rt("/{database:Item}/view")
def post(request, database: items.Item, sql: str, view: str):
    "Actually create a view in the database."
    assert isinstance(database, items.Database)
    with database as cnx:
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


@rt("/{database:Item}/plot/{tableview}")
def get(session, request, database: items.Item, tableview: str):
    "Add a plot for the given table or view in in the database."
    assert isinstance(database, items.Database)
    info = database.get_tableview_info(tableview)
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
                Header(
                    components.get_database_icon(),
                    A(database.title, href=database.url),
                ),
                get_database_overview(database),
            ),
            Card(
                Header("X/Y plot"),
                Form(
                    Input(type="hidden", name="plot", value="xy"),
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
                        Label(
                            "X axis",
                            Select(
                                Option("Select column", selected=True, disabled=True),
                                *[Option(column["name"]) for column in info["columns"]],
                                name="x",
                            ),
                        )
                    ),
                    Fieldset(
                        Label(
                            "Y axis",
                            Select(
                                Option("Select column", selected=True, disabled=True),
                                *[Option(column["name"]) for column in info["columns"]],
                                name="y",
                            ),
                        )
                    ),
                    Fieldset(
                        Legend("Type"),
                        Input(type="radio", id="scatter", name="type", value="scatter"),
                        Label("Scatter", htmlFor="scatter"),
                        Input(type="radio", id="line", name="type", value="line"),
                        Label("Line", htmlFor="line"),
                    ),
                    Input(type="submit", value="Add X/Y plot"),
                    action=f"{database.url}/plot/{tableview}",
                    method="POST",
                ),
            ),
            Form(
                Input(
                    type="submit",
                    value="Cancel",
                    cls="secondary",
                ),
                action=database.url,
                method="GET",
            ),
            cls="container",
        ),
    )


@rt("/{database:Item}/plot/{tableview}")
def post(session, request, database: items.Item, tableview: str, form: dict):
    "Actually add a plot for the given table or view in in the database."
    assert isinstance(database, items.Database)
    ic(form)
    info = database.get_tableview_info(tableview)
    title = form["title"]
    if database.frontmatter.get("plots", {}).get(title):
        raise errors.Error(f"plot '{title}' already defined")
    result = dict(tableview=tableview, name=items.normalize(title), plot=form["plot"])
    database.frontmatter.setdefault("plots", {})[title] = result
    match form["plot"]:
        case "xy":
            result["x"] = form["x"]
            result["y"] = form["y"]
            result["type"] = form["type"]
        case "barchart":
            pass
        case "piechart":
            pass
        case _:
            raise NotImplementedError
    database.write()
    return components.redirect(database.url)


@rt("/{database:Item}/plot/{tableview}/{plotname}")
def get(session, request, database: items.Item, tableview: str, plotname: str):
    "Edit the named plot for the given table or view in in the database."
    assert isinstance(database, items.Database)
    info = database.get_tableview_info(tableview)
    raise NotImplementedError


@rt("/{database:Item}/plot/{tableview}/{plotname}")
def post(
    session, request, database: items.Item, tableview: str, plotname: str, form: dict
):
    "Actually ddit the named plot for the given table or view in in the database."
    assert isinstance(database, items.Database)
    info = database.get_tableview_info(tableview)
    raise NotImplementedError


def get_database_overview(database, display=False, add_plot=False):
    "Get an overview of the basic structure of the database."
    rows = []
    items = list(database.tables().items()) + list(database.views().items())
    for name, item in items:
        if add_plot:
            add_plot_button = A(
                "Add plot",
                href=f"{database.url}/plot/{name}",
                role="button",
                cls="thin",
            )
        else:
            add_plot_button = ""
        spec = [
            Li(
                f"{r['name']} {r['type']} {not r['null'] and 'NOT NULL' or ''} {r['primary'] and 'PRIMARY KEY' or ''}"
            )
            for r in item["columns"]
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
                    add_plot_button,
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
