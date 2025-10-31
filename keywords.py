"Keyword pages."

from fasthtml.common import *

import components
import constants
import entries
import settings

app, rt = components.get_app_rt()


@rt("/")
def get():
    "List of keywords."
    return (
        Title("Keywords"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li("Keywords"),
                    Li(components.search_form()),
                ),
                cls="keyword",
            ),
            cls="container",
        ),
        Main(
            Table(
                Thead(
                    Tr(
                        Th("Keyword"),
                        Th("# total entries"),
                        Th(),
                    ),
                ),
                Tbody(
                    *[
                        Tr(
                            Td(A(kw, href=f"/keywords/{kw}")),
                            Td(entries.get_total_keyword_entries(kw)),
                            Td(
                                A(
                                    "Delete",
                                    href=f"/keywords/{kw}/delete",
                                    role="button",
                                    cls="outline thin",
                                ),
                                cls="right",
                            ),
                        )
                        for kw in settings.get_all_keywords()
                    ],
                ),
                cls="compressed",
            ),
            Div(
                Div(
                    Form(
                        Fieldset(
                            Input(
                                type="text",
                                name="keyword",
                                placeholder="Add keyword...",
                                required=True,
                            ),
                        ),
                        Input(
                            type="submit",
                            value="Add",
                        ),
                        action="/keywords",
                        method="POST",
                    ),
                ),
                Div(),
                cls="grid",
            ),
            cls="container",
        ),
    )


@rt("/")
def post(keyword: str):
    "Actually add a keyword."
    keyword = keyword.strip()
    if not keyword:
        raise components.Error("No new keyword provided.")
    try:
        settings.keywords.add(keyword)
    except ValueError as error:
        raise components.Error(error)
    settings.write()
    return components.redirect("/keywords")


@rt("/{keyword}")
def get(keyword: str, page: int = 1):
    "Display list of entries containing the provided keyword."
    keyword = keyword.strip()
    if not keyword:
        return components.redirect("/keywords")
    rows = [
        Tr(
            Td(keyword),
            Td(
                A(
                    "Delete",
                    role="button",
                    href=f"/keywords/{keyword}/delete",
                    cls="outline thin",
                )
            ),
        )
    ]
    return components.get_entries_table_page(
        f"Keyword '{keyword}'",
        entries.get_keyword_entries(keyword),
        page,
        f"/keywords/{keyword}",
        after=Article(Header("Synonyms"), Table(Tbody(*rows))),
    )


@rt("/{keyword}/delete")
def get(keyword: str):
    "Ask for confirmation to delete the keyword."
    keyword = keyword.strip()
    if not keyword:
        return components.redirect("/keywords")
    if not (keyword in settings.keywords):
        return components.redirect("/keywords")
    return (
        Title(f"Delete {keyword}?"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li(f"Delete {keyword}?"),
                ),
                cls="keyword",
            ),
            cls="container",
        ),
        Main(
            P(f"Really delete the keyword '{keyword}'?"),
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
                action=f"/keywords/{keyword}/delete",
                method="POST",
            ),
            cls="container",
        ),
    )


@rt("/{keyword}/delete")
def post(keyword: str, action: str):
    "Actually delete a keyword. This will delete it from all entries."
    if "yes" in action.casefold():
        settings.keywords.discard(keyword)
        settings.write()
        for entry in entries.lookup.values():
            entry.remove_keyword(keyword)
        entries.set_all_relations()
        return components.redirect("/keywords")
    else:
        return components.redirect(f"/keywords/{keyword}")
