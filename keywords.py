"Keyword pages."

from fasthtml.common import *

import components
import constants
import entries
import settings

app, rt = components.fast_app()


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
                ),
                Ul(
                    Li(components.search_form()),
                    Li(
                        Details(
                            Summary("Add..."),
                            Ul(
                                Li(A("Note", href="/note/")),
                                Li(A("Link", href="/link/")),
                                Li(A("File", href="/file/")),
                            ),
                            cls="dropdown",
                        ),
                    ),
                ),
                style=constants.KEYWORD_NAV_STYLE,
            ),
            cls="container",
        ),
        Main(
            Table(
                Tbody(
                    *[Tr(Td(kw),
                         Td(Form(Input(type="hidden", name="keyword", value=kw),
                                 Input(type="submit", value="Delete",
                                       style="height: 32px; width: 20%; padding: 0; margin: 0;"),
                                 action=f"/keywords/{kw}/delete",
                                 method="POST"),
                            style="text-align: right;"))
                      for kw in sorted(settings.lookup["keywords"].values(),
                                       key=lambda kw: kw.casefold())
                      ],
                ),
            ),
            Form(
                Input(
                    type="text",
                    name="keyword",
                    placeholder="New keyword...",
                    required=True,
                ),
                Input(
                    type="submit",
                    value="Add",
                ),
                action="/keywords",
                method="POST",
            ),
            cls="container",
        ),
        Footer(
            Hr(),
            Div(
                Div(session["auth"]),
                Div(f"v {constants.VERSION}", style="text-align: right;"),
                cls="grid",
            ),
            cls="container",
        ),
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
def get(sesion, keyword: str):
    "Display list of entries containing the provided keyword."
    keyword = cleanup(keyword)
    if not keyword:
        return components.redirect("/keywords")
    


@rt("/{keyword}/delete")
def post(session, keyword: str):
    "Actually delete a keyword."
    settings.lookup["keywords"].pop(keyword, None)
    settings.write()
    entries.set_all_keywords_relations()
    return components.redirect("/keywords")
    

def cleanup(keyword):
    "Return cleaned-up (but not casefolded) keyword."
    return keyword.strip().replace("/", "-").replace(".", "-")
