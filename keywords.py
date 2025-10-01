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
                            Td(A(kw[1], href=f"/keywords/{kw[0]}")),
                            Td(f"{count(kw[0])} entries"),
                            Td(
                                A(
                                    "Delete",
                                    href=f"/keywords/{kw[0]}/delete",
                                    role="button",
                                    cls="outline",
                                    style="padding: 4px 10px;",
                                ),
                                style="text-align: right;",
                            ),
                        )
                        for kw in sorted(settings.lookup["keywords"].items())
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
    keyword = cleanup(keyword)
    if not keyword:
        raise components.Error("No new keyword provided.")
    settings.lookup["keywords"][keyword.casefold()] = keyword
    settings.write()
    entries.set_all_keywords_relations()
    return components.redirect("/keywords")


@rt("/{keyword}")
def get(session, keyword: str, page: int = 1):
    "Display list of entries containing the provided keyword."
    keyword = cleanup(keyword)
    if not keyword:
        return components.redirect("/keywords")
    page = max(1, page)
    canonical_keyword = keyword.casefold()
    keyword = settings.lookup["keywords"].get(canonical_keyword)
    if not keyword:
        return components.redirect("/keywords")
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
                            A("Delete", href=f"/keywords/{keyword}/delete"),
                            A("Add note...", href="/note"),
                            A("Add link...", href="/link"),
                            A("Add file...", href="/file"),
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
            components.get_entries_table(
                entries.get_recent_entries(
                    start=(page - 1) * constants.MAX_PAGE_ENTRIES,
                    end=page * constants.MAX_PAGE_ENTRIES,
                    keyword=canonical_keyword,
                )
            ),
            components.get_table_pager(
                page, count(canonical_keyword), action=f"/keywords/{keyword}"
            ),
            cls="container",
        ),
        components.get_footer(),
    )


@rt("/{keyword}/delete")
def get(session, keyword: str):
    "Ask for confirmation to delete the keyword."
    keyword = cleanup(keyword)
    if not keyword:
        return components.redirect("/keywords")
    canonical_keyword = keyword.casefold()
    keyword = settings.lookup["keywords"].get(canonical_keyword)
    if not keyword:
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
                action=f"/keywords/{canonical_keyword}/delete",
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
        settings.lookup["keywords"].pop(keyword, None)
        settings.write()
        entries.set_all_keywords_relations()
        return components.redirect("/keywords")
    else:
        return components.redirect(f"/keywords/{keyword}")


def cleanup(keyword):
    "Return cleaned-up (but not casefolded) keyword."
    return keyword.strip().replace("/", "-").replace(".", "-")


def count(keyword):
    "Return the number of entries having the keyword."
    return len([e for e in entries.lookup.values() if keyword in e.keywords])
