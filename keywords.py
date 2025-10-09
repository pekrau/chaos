"Keyword pages."

from fasthtml.common import *

import components
import constants
import entries
import settings

app, rt = components.get_app_rt()


@rt("/")
def get(session):
    "List of keywords."
    return (
        Title("chaos"),
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
                Tbody(
                    *[
                        Tr(
                            Td(
                                A(kw, href=f"/keywords/{kw}"),
                                " ",
                                Small(", ".join([s for s in list(syn) if s != kw])),
                            ),
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
                        for kw, syn in sorted(
                            settings.canonical_keywords.items(),
                            key=lambda k: k[0].casefold(),
                        )
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
                            Small("keyword: synonym [optional]"),
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
def post(session, keyword: str):
    "Actually add a keyword."
    keyword = keyword.strip()
    if not keyword:
        raise components.Error("No new keyword provided.")
    try:
        settings.add_keyword_canonical(keyword)
    except ValueError as error:
        raise components.Error(error)
    settings.write()
    entries.set_all_keywords_relations()
    return components.redirect("/keywords")


@rt("/{keyword}")
def get(session, keyword: str, page: int = 1):
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
    rows.extend(
        [
            Tr(
                Td(synonym, " (synonym)"),
                Td(
                    A(
                        "Delete",
                        role="button",
                        href=f"/keywords/{synonym}/delete",
                        cls="outline thin",
                    )
                ),
            )
            for synonym in [
                kw
                for kw in settings.canonical_keywords.get(keyword, [])
                if kw != keyword
            ]
        ]
    )
    return components.get_entries_table_page(
        session,
        f"Keyword '{keyword}'",
        entries.get_keyword_entries(keyword),
        page,
        f"/keywords/{keyword}",
        after=Article(Header("Synonyms"), Table(Tbody(*rows))),
    )


@rt("/{keyword}/delete")
def get(session, keyword: str):
    "Ask for confirmation to delete the keyword."
    keyword = keyword.strip()
    if not keyword:
        return components.redirect("/keywords")
    if not (keyword in settings.keywords or keyword in settings.canonical_keywords):
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
def post(session, keyword: str, action: str):
    "Actually delete a keyword."
    if "yes" in action.casefold():
        # The given keyword is a canonical keyword: remove all its text keywords.
        if keyword in settings.canonical_keywords:
            for kw in settings.canonical_keywords[keyword]:
                settings.keywords.pop(kw)
            settings.canonical_keywords.pop(keyword)
        # The given keyword is a text keyword; remove it.
        elif keyword in settings.keywords:
            canonical = settings.keywords.pop(keyword)
            settings.canonical_keywords[canonical].remove(keyword)
        settings.write()
        entries.set_all_keywords_relations()
        return components.redirect("/keywords")
    else:
        return components.redirect(f"/keywords/{keyword}")
