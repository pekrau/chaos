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
                    Li(components.chaos_icon()),
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
                                Small(", ".join([k for k in list(kws) if k != kw])),
                            ),
                            Td(f"{entries.count(kw)} entries"),
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
                        for kw, kws in sorted(settings.canonical_keywords.items())
                    ],
                ),
            ),
            Div(
                Div(
                    Form(
                        Input(
                            type="text",
                            name="keyword",
                            placeholder="Add keyword...",
                            required=True,
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
        components.get_footer(),
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
    page = max(1, page)
    return (
        Title("chaos"),
        Script(src="/clipboard.min.js"),
        Script("new ClipboardJS('.to_clipboard');"),
        Header(
            Nav(
                Ul(
                    Li(components.chaos_icon()),
                    Li(Strong(keyword)),
                    Li(
                        components.get_dropdown_menu(
                            A("Add note...", href="/note/"),
                            A("Add link...", href="/link/"),
                            A("Add file...", href="/file/"),
                            A("Keywords", href="/keywords"),
                        ),
                    ),
                    Li(components.search_form()),
                ),
                cls="keyword",
            ),
            cls="container",
        ),
        Main(
            Table(Tbody(*rows)),
            components.get_entries_table(
                entries.get_recent_entries(
                    start=(page - 1) * constants.MAX_PAGE_ENTRIES,
                    end=page * constants.MAX_PAGE_ENTRIES,
                    keyword=keyword,
                )
            ),
            components.get_table_pager(
                page, entries.count(keyword), action=f"/keywords/{keyword}"
            ),
            cls="container",
        ),
        components.get_footer(),
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
                    Li(components.chaos_icon()),
                    Li("Delete"),
                    Li(Strong(keyword)),
                ),
                cls="keyword",
            ),
            cls="container",
        ),
        Main(
            P("Really delete the keyword?"),
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
        components.get_footer(),
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
