"Person item pages."

from fasthtml.common import *
from fasthtml.pico import Card

import components
import constants
import items

app, rt = components.get_app_rt()


@rt("/")
def get():
    "Form for adding a person."
    return (
        Title("Add person"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu()),
                    Li("Add ", components.get_person_icon(), "person"),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                components.get_title_input(autofocus=True),
                Div(
                    Label(
                        Strong(NotStr("&#9733;")),
                        " Birth",
                        Input(type="date", name="birth"),
                    ),
                    Label(
                        Strong(NotStr("&#8224;")),
                        " Death",
                        Input(type="date", name="death"),
                    ),
                    cls="grid",
                ),
                Fieldset(
                    Input(type="radio", name="sex", id="male", value=constants.MALE),
                    Label("Male", htmlFor="male"),
                    Input(
                        type="radio", name="sex", id="female", value=constants.FEMALE
                    ),
                    Label("Female", htmlFor="female"),
                ),
                Fieldset(
                    Input(type="text", name="father", placeholder="Father..."),
                    Input(type="text", name="mother", placeholder="Mother..."),
                    cls="grid",
                ),
                components.get_text_input(),
                components.get_tags_input(),
                Input(type="submit", value="Add"),
                action="/person/",
                method="POST",
            ),
            components.get_cancel_form("/"),
            cls="container",
        ),
    )


@rt("/")
def post(
    title: str,
    text: str,
    birth: str = None,
    death: str = None,
    sex: str = None,
    father: str = "",
    mother: str = "",
    tags: list[str] = None,
):
    "Actually create and add the person."
    person = items.Person()
    person.title = title
    person.birth = birth
    person.death = death
    person.sex = sex
    person.father = father.lstrip("[").rstrip("]") or None
    person.mother = mother.lstrip("[").rstrip("]") or None
    person.text = text.strip()
    person.tags = tags
    person.write()
    return components.redirect(person.url)


@rt("/{person:Item}")
def get(person: items.Item, tags_page: int = 1, refs_page: int = 1):
    "View the person."
    assert isinstance(person, items.Person)
    relatives = [
        Div(
            "Father ", components.get_item_link(person.father) if person.father else "-"
        ),
        Div(
            "Mother ", components.get_item_link(person.mother) if person.mother else "-"
        ),
    ]
    if children := person.children:
        parts = []
        for child in children:
            if parts:
                parts.append(", ")
            parts.append(components.get_item_link(child))
        relatives.append(Div("Children ", *parts))
    if siblings := person.siblings:
        parts = []
        for sibling in siblings:
            if parts:
                parts.append(", ")
            parts.append(components.get_item_link(sibling))
        relatives.append(Div("Siblings ", *parts))

    return (
        Title(person),
        components.get_clipboard_script(),
        components.get_header_item_view(person),
        Main(
            Card(
                Span(Strong(NotStr("&#9733;")), " Birth ", person.birth or "-"),
                Span(Strong(NotStr("&#8224;")), " Death ", person.death or "-"),
                (
                    components.get_icon("gender-male.svg")
                    if person.sex == constants.MALE
                    else (
                        components.get_icon("gender-female.svg")
                        if person.sex == constants.FEMALE
                        else ""
                    )
                ),
                cls="grid",
            ),
            Card(*relatives) if relatives else "",
            components.get_text_card(person),
            Form(
                components.get_refs_card(person, refs_page),
                components.get_tags_card(person, tags_page),
                action=person.url,
            ),
            cls="container",
        ),
        components.get_footer_item_view(person),
        components.get_clipboard_activate(),
    )


@rt("/{person:Item}/edit")
def get(person: items.Item):
    "Form for editing a person."
    assert isinstance(person, items.Person)
    return (
        *components.get_header_item_edit(person),
        Main(
            Form(
                components.get_title_input(person.title),
                Div(
                    Label(
                        Strong(NotStr("&#9733;")),
                        " Birth",
                        Input(type="date", name="birth", value=person.birth),
                    ),
                    Label(
                        Strong(NotStr("&#8224;")),
                        " Death",
                        Input(type="date", name="death", value=person.death),
                    ),
                    cls="grid",
                ),
                Fieldset(
                    Input(
                        type="radio",
                        name="sex",
                        id="male",
                        value=constants.MALE,
                        checked=person.sex == constants.MALE,
                    ),
                    Label("Male", htmlFor="male"),
                    Input(
                        type="radio",
                        name="sex",
                        id="female",
                        value=constants.FEMALE,
                        checked=person.sex == constants.FEMALE,
                    ),
                    Label("Female", htmlFor="female"),
                ),
                Fieldset(
                    Input(
                        type="text",
                        name="father",
                        placeholder="Father...",
                        value=person.father.id if person.father else "",
                    ),
                    Input(
                        type="text",
                        name="mother",
                        placeholder="Mother...",
                        value=person.mother.id if person.mother else "",
                    ),
                    cls="grid",
                ),
                components.get_text_input(person.text),
                components.get_tags_input(person.tags),
                Input(type="submit", value="Save"),
                action=f"{person.url}/edit",
                method="POST",
            ),
            components.get_cancel_form(person.url),
            cls="container",
        ),
    )


@rt("/{person:Item}/edit")
def post(
    person: items.Item,
    title: str,
    text: str,
    birth: str = None,
    death: str = None,
    sex: str = None,
    father: str = "",
    mother: str = "",
    tags: list[str] = None,
):
    "Actually edit the person."
    assert isinstance(person, items.Person)
    person.title = title
    person.birth = birth
    person.death = death
    person.sex = sex
    person.father = father.lstrip("[").rstrip("]") or None
    person.mother = mother.lstrip("[").rstrip("]") or None
    person.text = text.strip()
    person.tags = tags
    person.write()
    return components.redirect(person.url)


@rt("/{person:Item}/copy")
def get(person: items.Item):
    "Form for making a copy of the person."
    assert isinstance(person, items.Person)
    return (
        Title(f"Copy '{person}'"),
        Header(
            Nav(
                Ul(
                    Li(components.get_nav_menu(person)),
                    Li("Copy ", components.get_person_icon(), person),
                ),
            ),
            cls="container",
        ),
        Main(
            Form(
                Input(
                    type="text",
                    name="title",
                    value=person.title,
                    placeholder="Title...",
                    required=True,
                ),
                Input(type="submit", value="Copy person"),
                action=f"{person.url}/copy",
                method="POST",
            ),
            components.get_cancel_form(person.url),
            cls="container",
        ),
    )


@rt("/{source:Item}/copy")
def post(source: items.File, title: str):
    "Actually copy the person."
    assert isinstance(source, items.Person)
    person = items.Person()
    person.title = title
    person.birth = source.birth
    person.death = source.death
    person.sex = source.sex
    person.father = source.father
    person.mother = source.mother
    person.text = source.text
    person.tags = source.tags
    person.write()
    return components.redirect(f"{person.url}/edit")


@rt("/{person:Item}/delete")
def get(person: items.Item):
    "Ask for confirmation to delete the person."
    assert isinstance(person, items.Person)
    return (
        *components.get_header_item_edit(person),
        Main(
            H3("Really delete the person?"),
            Form(
                Input(type="submit", value="Yes, delete"),
                action=f"{person.url}/delete",
                method="POST",
            ),
            components.get_cancel_form(person.url),
            cls="container",
        ),
    )


@rt("/{person:Item}/delete")
def post(person: items.Item):
    "Actually delete the person."
    assert isinstance(person, items.Person)
    person.delete()
    return components.redirect()
