"Article reference item pages."

import urllib.parse

from fasthtml.common import *

import components
import constants
import items

app, rt = components.get_app_rt()


@rt("/")
def get(request):
    "Form for adding a article reference."
    title = "Add article"
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
                ),
                components.get_title_input(),
                Textarea(
                    name="authors",
                    rows=2,
                    placeholder="Authors...",
                ),
                Div(
                    Input(
                        name="published",
                        placeholder="Published...",
                    ),
                    Input(
                        name="doi",
                        placeholder="DOI...",
                    ),
                    Input(
                        name="pmid",
                        placeholder="PubMed...",
                    ),
                ),
                Div(
                    Input(
                        name="journal",
                        placeholder="Journal...",
                    ),
                    Input(
                        name="volume",
                        placeholder="Volume...",
                    ),
                    Input(
                        name="issue",
                        placeholder="Issue...",
                    ),
                    Input(
                        name="pages",
                        placeholder="Pages...",
                    ),
                    cls="grid",
                ),
                components.get_text_input(),
                Input(type="submit", value="Add article"),
                action="/article/",
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
    published: str,
    doi: str,
    pmid: str,
    journal: str,
    volume: str,
    issue: str,
    pages: str,
    text: str,
):
    "Actually add the article."
    id = utils.normalize(id.strip())
    if not id:
        raise KeyError("no identifier provided")
    if id in items.lookup:
        raise KeyError(f"item '{id}' already exists")
    article = items.Article(constants.DATA_DIR / f"{id}.md")
    article.title = title.strip() or "no title"
    article.frontmatter["authors"] = list(
        filter(None, [a.strip() for a in authors.strip().split("\n")])
    )
    article.frontmatter["published"] = published.strip()
    article.frontmatter["doi"] = doi.strip()
    article.frontmatter["pmid"] = pmid.strip()
    article.frontmatter["journal"] = journal.strip()
    article.frontmatter["volume"] = volume.strip()
    article.frontmatter["issue"] = issue.strip()
    article.frontmatter["pages"] = pages.strip()
    article.text = text.strip()
    article.write()
    return components.redirect(article.url)


@rt("/{article:Item}")
def get(article: items.Item):
    "View the article."
    assert isinstance(article, items.Article)
    return (
        Title(article.title),
        components.clipboard_script(),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(article, copy=False)),
                    Li(components.get_article_icon(), article.title),
                    Li(components.to_clipboard(article)),
                ),
                Ul(
                    Li(components.get_shortcuts_menu(article)),
                ),
            ),
            cls="container",
        ),
        Main(
            Card("; ".join(article.authors)),
            Card(
                Div(article.published, title="Published"),
                (
                    A(
                        article.doi,
                        href=constants.DOI_URL.format(doi=article.doi),
                        target="_blank",
                    )
                    if article.doi
                    else ""
                ),
                (
                    A(
                        f"PubMed {article.pmid}",
                        href=constants.PUBMED_URL.format(pmid=article.pmid),
                        target="_blank",
                    )
                    if article.pmid
                    else ""
                ),
                cls="grid",
            ),
            Card(
                Span(article.journal, title="Journal"),
                " ",
                Strong(article.volume or "-", title="Volume"),
                " ",
                Span(f"({article.issue or '-'})", title="Issue"),
                " ",
                Span(article.pages or "-", title="Pages"),
            ),
            components.get_text_card(article),
            components.get_xrefs_card(article),
            cls="container",
        ),
        Footer(
            Hr(),
            Div(
                Div(article.modified_local),
                Div(f"{article.size} bytes"),
                cls="grid",
            ),
            cls="container",
        ),
        components.clipboard_activate(),
    )


@rt("/{article:Item}/edit")
def get(request, article: items.Item):
    "Form for editing a article."
    assert isinstance(article, items.Article)
    title = f"Edit '{article.title}'"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(article, copy=False)),
                    Li(title),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                components.get_title_input(article.title),
                Textarea(
                    "\n".join(article.authors),
                    name="authors",
                    rows=4,
                ),
                Div(
                    Label(
                        "Published",
                        Input(name="published", value=article.published or ""),
                    ),
                    Label("DOI", Input(name="doi", value=article.doi or "")),
                    Label(
                        "PubMed",
                        Input(name="pmid", value=article.pmid or ""),
                    ),
                    cls="grid",
                ),
                Div(
                    Label(
                        "Journal",
                        Input(name="journal", value=article.journal or ""),
                    ),
                    Label(
                        "Volume",
                        Input(name="volume", value=article.volume or ""),
                    ),
                    Label(
                        "Issue",
                        Input(name="issue", value=article.issue or ""),
                    ),
                    Label(
                        "Pages",
                        Input(name="pages", value=article.pages or ""),
                    ),
                    cls="grid",
                ),
                components.get_text_input(),
                Input(type="submit", value="Save"),
                action=f"{article.url}/edit",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/{article:Item}/edit")
def post(
    article: items.Item,
    title: str,
    authors: str,
    doi: str,
    pmid: str,
    journal: str,
    volume: str,
    issue: str,
    pages: str,
    published: str,
    text: str,
):
    "Actually edit the article."
    assert isinstance(article, items.Article)
    article.title = title.strip()
    article.frontmatter["authors"] = list(
        filter(None, [a.strip() for a in authors.strip().split("\n")])
    )
    article.frontmatter["published"] = published.strip()
    article.frontmatter["doi"] = doi.strip()
    article.frontmatter["pmid"] = pmid.strip()
    article.frontmatter["journal"] = journal.strip()
    article.frontmatter["volume"] = volume.strip()
    article.frontmatter["issue"] = issue.strip()
    article.frontmatter["pages"] = pages.strip()
    article.text = text.strip()
    article.write()
    return components.redirect(article.url)


@rt("/{article:Item}/delete")
def get(request, article: items.Item):
    "Ask for confirmation to delete the article."
    assert isinstance(article, items.Article)
    redirect = urllib.parse.urlsplit(request.headers["Referer"]).path
    if redirect == f"/article/{article.id}":
        redirect = "/articles"
    title = f"Delete '{article.title}'"
    return (
        Title(title),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(article, copy=False)),
                    Li(title),
                ),
            ),
            cls="container",
        ),
        Main(
            H3("Really delete the article? All data will be lost."),
            Form(
                Input(
                    type="hidden",
                    name="redirect",
                    value=redirect,
                ),
                Input(type="submit", value="Yes, delete"),
                action=f"{article.url}/delete",
                method="POST",
            ),
            components.get_cancel_form(request.headers["Referer"]),
            cls="container",
        ),
    )


@rt("/{article:Item}/delete")
def post(article: items.Item, redirect: str):
    "Actually delete the article."
    assert isinstance(article, items.Article)
    article.delete()
    return components.redirect(redirect)
