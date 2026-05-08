"Book reference item pages."

import datetime as dt
import urllib.parse

from fasthtml.common import *

import components
import constants
import items
import utils

app, rt = components.get_app_rt()


@rt("/")
def get():
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
                    aria_describedby="id-helper",
                ),
                Small(
                    "The identifier must have the form 'lastname-year'.", id="id-helper"
                ),
                components.get_title_input(),
                Textarea(
                    name="authors",
                    rows=2,
                    placeholder="Authors...",
                    aria_describedby="authors-helper",
                    required=True,
                ),
                Small(
                    "Authors: 'Family name, first name(s)' separated by newlines.",
                    id="authors-helper",
                ),
                Div(
                    Div(
                        Input(
                            name="year",
                            placeholder="Year...",
                            aria_describedby="year-helper",
                            required=True,
                        ),
                        Small("Original year of publication.", id="year-helper"),
                    ),
                    Input(
                        name="publisher",
                        placeholder="Publisher...",
                    ),
                    Div(
                        Input(
                            name="published",
                            placeholder="Published...",
                            aria_describedby="published-helper",
                        ),
                        Small("Date for this edition.", id="published-helper"),
                    ),
                    Div(
                        Select(
                            Option("Language", selected=True, value=""),
                            *[
                                Option(lang[1], value=lang[0])
                                for lang in constants.LANGUAGES.items()
                            ],
                            name="language",
                        ),
                        Small(),
                    ),
                    Input(
                        name="isbn",
                        placeholder="ISBN...",
                    ),
                    cls="grid",
                ),
                components.get_text_input(),
                components.get_tags_input(),
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
    text: str,
    publisher: str = None,
    published: str = None,
    language: str = None,
    isbn: str = None,
    tags: list[str] = None,
):
    "Actually add the book."
    id = utils.normalize(id.strip())
    if not id:
        raise KeyError("no identifier provided")
    if id in items.lookup:
        raise KeyError(f"item '{id}' already exists")
    # Special handling, since 'id' is defined by the user, not the 'title'.
    book = items.Book(constants.DATA_DIR / f"{id}.md")
    items.lookup[book.id] = book
    book.title = title.strip() or "no title"
    book.authors = authors
    book.year = year
    book.publisher = publisher
    book.published = published
    book.language = language
    book.isbn = isbn
    book.text = text.strip()
    book.tags = tags
    book.write()
    return components.redirect(book.url)


@rt("/{book:Item}")
def get(book: items.Item, page: int = 1, tags_page: int = 1, refs_page: int = 1):
    "View the book."
    assert isinstance(book, items.Book)
    return (
        Title(book),
        components.get_clipboard_script(),
        components.get_header_item_view(book, copy=False),
        Main(
            Card("; ".join(book.authors)),
            Card(
                Div(book.year, title="Year"),
                Div(book.publisher or "", title="Publisher"),
                Div(book.published or "", title="Published"),
                Div(constants.LANGUAGES.get(book.language, ""), title="Language"),
                A(
                    f"ISBN {book.isbn}",
                    href=constants.ISBN_URL.format(isbn=book.isbn),
                    target="_blank",
                ),
                cls="grid",
            ),
            components.get_text_card(book),
            Form(
                components.get_refs_card(book, refs_page),
                components.get_tags_card(book, tags_page),
                action=book.url,
            ),
            cls="container",
        ),
        components.get_footer_item_view(book),
        components.get_clipboard_activate(),
    )


@rt("/{book:Item}/edit")
def get(book: items.Item):
    "Form for editing a book."
    assert isinstance(book, items.Book)
    return (
        *components.get_header_item_edit(book),
        Main(
            Form(
                components.get_title_input(book.title),
                Textarea(
                    "\n".join(book.authors),
                    name="authors",
                    rows=4,
                    aria_describedby="authors-helper",
                    required=True,
                ),
                Small(
                    "Authors: 'Family name, first name(s)' separated by newlines.",
                    id="authors-helper",
                ),
                Div(
                    Label(
                        "Year",
                        Input(
                            name="year",
                            value=book.year,
                            aria_describedby="year-helper",
                            required=True,
                        ),
                        Small("Original year of publication.", id="year-helper"),
                    ),
                    Label(
                        "Publisher",
                        Input(name="publisher", value=book.publisher or ""),
                    ),
                    Label(
                        "Published",
                        Input(
                            name="published",
                            value=book.published or "",
                            aria_describedby="published-helper",
                        ),
                        Small("Date for this edition.", id="published-helper"),
                    ),
                    Label(
                        "Language",
                        Select(
                            Option("", value=""),
                            *[
                                Option(
                                    lang[1],
                                    value=lang[0],
                                    selected=book.language == lang[0],
                                )
                                for lang in constants.LANGUAGES.items()
                            ],
                            name="language",
                        ),
                    ),
                    Label("ISBN", Input(name="isbn", value=book.isbn)),
                    cls="grid",
                ),
                components.get_text_input(book.text),
                components.get_tags_input(book.tags),
                Input(type="submit", value="Save"),
                action=f"{book.url}/edit",
                method="POST",
            ),
            components.get_cancel_form(book.url),
            cls="container",
        ),
    )


@rt("/{book:Item}/edit")
def post(
    book: items.Item,
    title: str,
    authors: str,
    year: str,
    text: str,
    publisher: str = None,
    published: str = None,
    language: str = None,
    isbn: str = None,
    tags: list[str] = None,
):
    "Actually edit the book."
    assert isinstance(book, items.Book)
    book.title = title.strip() or "no title"
    book.authors = authors
    book.year = year
    book.publisher = publisher
    book.published = published
    book.language = language
    book.isbn = isbn
    book.text = text.strip()
    book.tags = tags
    book.write()
    return components.redirect(book.url)


@rt("/{book:Item}/delete")
def get(book: items.Item):
    "Ask for confirmation to delete the book."
    assert isinstance(book, items.Book)
    title = f"Delete '{book}'"
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
                Input(type="submit", value="Yes, delete"),
                action=f"{book.url}/delete",
                method="POST",
            ),
            components.get_cancel_form(book.url),
            cls="container",
        ),
    )


@rt("/{book:Item}/delete")
def post(book: items.Item):
    "Actually delete the book."
    assert isinstance(book, items.Book)
    book.delete()
    return components.redirect()
