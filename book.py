"Book reference item pages."

import urllib.parse

from fasthtml.common import *

import components
import constants
import items

app, rt = components.get_app_rt()


@rt("/")
def get(request):
    "Form for adding a book reference."
    title = "Add book"
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
                Input(
                    name="id",
                    placeholder="Identifier...",
                    required=True,
                ),
                components.get_title_input(),
                Textarea(
                    name="authors",
                    rows=2,
                    placeholder="Authors...",
                    required=True,
                ),
                Div(
                    Input(
                        name="year",
                        placeholder="Year...",
                        required=True,
                    ),
                    Input(
                        name="isbn",
                        placeholder="ISBN...",
                    ),
                    Input(
                        name="publisher",
                        placeholder="Publisher...",
                    ),
                    Input(
                        name="published",
                        placeholder="Published...",
                    ),
                    Select(
                        Option("Language", selected=True, disabled=True, value=""),
                        Option("English", value="en"),
                        Option("Svenska", value="se"),
                        name="language",
                    ),
                    cls="grid",
                ),
                components.get_text_input(),
                Input(type="submit", value="Add book"),
                action="/book/",
                method="POST",
            ),
            components.get_cancel_form("/"),
            cls="container",
        ),
    )


@rt("/")
def post(
    id: str,
    title: str,
    authors: str,
    year: str,
    isbn: str,
    publisher: str,
    published: str,
    language: str,
    text: str,
):
    "Actually add the book."
    id = utils.normalize(id.strip())
    if not id:
        raise KeyError("no identifier provided")
    if id in items.lookup:
        raise KeyError(f"item '{id}' already exists")
    book = items.Book(constants.DATA_DIR / f"{id}.md")
    book.title = title.strip() or "no title"
    book.frontmatter["authors"] = list(
        filter(None, [a.strip() for a in authors.strip().split("\n")])
    )
    book.frontmatter["year"] = year.strip()
    book.frontmatter["isbn"] = isbn.strip()
    book.frontmatter["publisher"] = publisher.strip()
    book.frontmatter["published"] = published.strip() or book.frontmatter["year"]
    book.frontmatter["language"] = language.strip()
    book.text = text.strip()
    book.write()
    return components.redirect(book.url)


@rt("/{book:Item}")
def get(book: items.Item):
    "View the book."
    assert isinstance(book, items.Book)
    return (
        Title(book.title),
        components.clipboard_script(),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(book, copy=False)),
                    Li(components.get_book_icon(), book.title),
                    Li(components.to_clipboard(book)),
                ),
                Ul(
                    Li(components.get_shortcuts_menu(book)),
                ),
            ),
            cls="container",
        ),
        Main(
            Card("; ".join(book.authors)),
            Card(
                Div(book.year, title="Year"),
                A(
                    f"ISBN {book.isbn}",
                    href=constants.ISBN_URL.format(isbn=book.isbn),
                    target="_blank",
                ),
                Div(book.publisher, title="Publisher"),
                Div(book.published, title="Published"),
                Div(constants.LANGUAGES.get(book.language, "")),
                cls="grid",
            ),
            components.get_text_card(book),
            components.get_xrefs_card(book),
            components.get_tags_card(book),
            cls="container",
        ),
        Footer(
            Hr(),
            Div(
                Div(book.modified_local),
                Div(f"{book.size} bytes"),
                Div(A("Source", href=f"/source/{book.id}"), cls="right"),
                cls="grid",
            ),
            cls="container",
        ),
        components.clipboard_activate(),
    )


@rt("/{book:Item}/edit")
def get(request, book: items.Item):
    "Form for editing a book."
    assert isinstance(book, items.Book)
    title = f"Edit '{book.title}'"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(book, copy=False)),
                    Li(title),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                components.get_title_input(book.title),
                Textarea(
                    "\n".join(book.authors),
                    name="authors",
                    rows=4,
                ),
                Div(
                    Label("Year", Input(name="year", value=book.year)),
                    Label("ISBN", Input(name="isbn", value=book.isbn)),
                    Label(
                        "Publisher",
                        Input(name="publisher", value=book.publisher or ""),
                    ),
                    Label(
                        "Published",
                        Input(name="published", value=book.published or ""),
                    ),
                    Label(
                        "Language",
                        Select(
                            Option("", disabled=True, value=""),
                            Option(
                                "English", value="en", selected=book.language == "en"
                            ),
                            Option(
                                "Svenska", value="se", selected=book.language == "se"
                            ),
                            name="language",
                        ),
                    ),
                    cls="grid",
                ),
                components.get_text_input(),
                Input(type="submit", value="Save"),
                action=f"{book.url}/edit",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/{book:Item}/edit")
def post(
    book: items.Item,
    title: str,
    authors: str,
    year: str,
    isbn: str,
    publisher: str,
    published: str,
    language: str,
    text: str,
):
    "Actually edit the book."
    assert isinstance(book, items.Book)
    book.title = title.strip() or "no title"
    book.frontmatter["authors"] = list(
        filter(None, [a.strip() for a in authors.strip().split("\n")])
    )
    book.frontmatter["year"] = year.strip()
    book.frontmatter["isbn"] = isbn.strip()
    book.frontmatter["publisher"] = publisher.strip()
    book.frontmatter["published"] = published.strip() or book.frontmatter["year"]
    book.frontmatter["language"] = language.strip()
    book.text = text.strip()
    book.write()
    return components.redirect(book.url)


@rt("/{book:Item}/delete")
def get(request, book: items.Item):
    "Ask for confirmation to delete the book."
    assert isinstance(book, items.Book)
    redirect = urllib.parse.urlsplit(request.headers["Referer"]).path
    if redirect == f"/book/{book.id}":
        redirect = "/"
    title = f"Delete '{book.title}'"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(book, copy=False)),
                    Li(title),
                ),
            ),
            cls="container",
        ),
        Main(
            H3("Really delete the book? All data will be lost."),
            Form(
                Input(
                    type="hidden",
                    name="redirect",
                    value=redirect,
                ),
                Input(type="submit", value="Yes, delete"),
                action=f"{book.url}/delete",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/{book:Item}/delete")
def post(book: items.Item, redirect: str):
    "Actually delete the book."
    assert isinstance(book, items.Book)
    book.delete()
    return components.redirect(redirect)
