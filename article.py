"Article reference item pages."

import urllib.parse

from fasthtml.common import *
from fasthtml.pico import Card

import bibtex
import components
import constants
import errors
import items
import utils

app, rt = components.get_app_rt()


@rt("/")
def get():
    "Form for creating a article reference."
    return (
        Title("Create article"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li("Create ", components.get_article_icon(), "article"),
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
                    "The identifier should have the form 'lastname-year[suffix]'.",
                    id="id-helper",
                ),
                Div(
                    Textarea(
                        name="bibtex_data",
                        rows=10,
                        placeholder="BibTex...",
                    ),
                    Div(
                        components.get_title_input(required=False),
                        Textarea(
                            name="authors",
                            rows=3,
                            placeholder="Authors...",
                            aria_describedby="authors-helper",
                        ),
                        Small(
                            "Authors: 'Family name, first name(s)' separated by newlines.",
                            id="authors-helper",
                        ),
                        Input(
                            name="journal",
                            placeholder="Journal...",
                        ),
                        Div(
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
                            cls="grid",
                        ),
                    ),
                    cls="grid",
                ),
                components.get_text_input(),
                components.get_tags_input(),
                Input(type="submit", value="Create"),
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
    bibtex_data: str,
    title: str,
    authors: str,
    text: str,
    journal: str,
    volume: str,
    issue: str,
    pages: str,
    published: str,
    doi: str,
    pmid: str,
    tags: list[str] = None,
):
    "Actually create the article."
    id = utils.normalize(id.strip())
    if not id:
        raise errors.Error("no identifier provided")
    if id in items.lookup:
        raise errors.Error(f"item '{id}' already exists")
    # Special handling, since 'id' is defined by the user, not the 'title'.
    article = items.Article(constants.DATA_DIR / f"{id}.md")
    items.lookup[article.id] = article
    if bibtex_data := bibtex_data.strip():
        entries = list(bibtex.parse(bibtex_data))
        entry = entries[0]
        if entry["type"] != "article":
            raise errors.Error("BibTex entry did not contain a article")
        article.title = entry["title"]
        article.authors = entry["authors"]
        article.journal = entry["journal"]
        article.volume = entry.get("volume")
        article.issue = entry.get("issue")
        article.pages = entry.get("pages")
        article.published = entry.get("published")
        article.doi = entry.get("doi")
        article.pmid = entry.get("pmid")
        if abstract := entry.get("abstract"):
            if text := text.strip():
                article.text = abstract + "\n\n" + text
            else:
                article.text = abstract
    else:
        article.title = title
        article.authors = authors
        article.journal = journal
        article.volume = volume or None
        article.issue = issue or None
        article.pages = pages or None
        article.published = published or None
        article.doi = doi or None
        article.pmid = pmid or None
        article.text = text.strip()  # Note: abstract also in text, if BibTex
    article.tags = tags
    article.write()
    return components.redirect(article.url)


@rt("/{article:Item}")
def get(article: items.Item, page: int = 1, tags_page: int = 1, refs_page: int = 1):
    "View the article."
    assert isinstance(article, items.Article)
    return (
        Title(article),
        components.get_clipboard_script(),
        components.get_header_item_view(article, copy=False),
        Main(
            Card("; ".join(article.authors), title="Authors"),
            Card(
                Div(
                    Span(article.journal, title="Journal"),
                    " ",
                    Strong(article.volume or "-", title="Volume"),
                    " ",
                    Span(f"({article.issue or '-'})", title="Issue"),
                    " ",
                    Span(article.pages or "-", title="Pages"),
                ),
                Div(article.published, title="Published"),
                (
                    A(
                        f"DOI {article.doi}",
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
            components.get_text_card(article),
            Form(
                components.get_refs_card(article, refs_page),
                components.get_tags_card(article, tags_page),
                action=article.url,
            ),
            cls="container",
        ),
        components.get_footer_item_view(article),
        components.get_clipboard_activate(),
    )


@rt("/{article:Item}/edit")
def get(article: items.Item):
    "Form for editing a article."
    assert isinstance(article, items.Article)
    return (
        *components.get_header_item_edit(article),
        Main(
            Form(
                components.get_title_input(article.title),
                Textarea(
                    "\n".join(article.authors),
                    name="authors",
                    rows=4,
                    aria_describedby="authors-helper",
                ),
                Small(
                    "Authors: 'Family name, first name(s)' separated by newlines.",
                    id="authors-helper",
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
                components.get_text_input(article.text),
                components.get_tags_input(article.tags),
                Input(type="submit", value="Save"),
                action=f"{article.url}/edit",
                method="POST",
            ),
            components.get_cancel_form(article.url),
            cls="container",
        ),
    )


@rt("/{article:Item}/edit")
def post(
    article: items.Item,
    title: str,
    authors: str,
    text: str,
    journal: str = None,
    volume: str = None,
    issue: str = None,
    pages: str = None,
    published: str = None,
    doi: str = None,
    pmid: str = None,
    tags: list[str] = None,
):
    "Actually edit the article."
    assert isinstance(article, items.Article)
    article.title = title
    article.authors = authors
    article.journal = journal
    article.volume = volume
    article.issue = issue
    article.pages = pages
    article.published = published
    article.doi = doi
    article.pmid = pmid
    article.text = text.strip()
    article.tags = tags
    article.write()
    return components.redirect(article.url)


@rt("/{article:Item}/delete")
def get(article: items.Item):
    "Ask for confirmation to delete the article."
    assert isinstance(article, items.Article)
    return (
        *components.get_header_item_delete(article),
        Main(
            H3("Really delete the article?"),
            Form(
                Input(type="submit", value="Yes, delete"),
                action=f"{article.url}/delete",
                method="POST",
            ),
            components.get_cancel_form(article.url),
            cls="container",
        ),
    )


@rt("/{article:Item}/delete")
def post(article: items.Item):
    "Actually delete the article."
    assert isinstance(article, items.Article)
    article.delete()
    return components.redirect()
