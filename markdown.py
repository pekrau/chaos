"Extension to Markdown; ref."

import marko
import marko.inline
import marko.helpers

import components
import constants
import items


class Ref(marko.inline.InlineElement):
    "Markdown extension for a cross-referenced item."

    pattern = constants.REF
    parse_children = False

    def __init__(self, match):
        self.ref = match.group(1)


class RefRenderer:
    "Output a link to the cross-referenced item."

    def render_ref(self, element):
        try:
            item = items.get(element.ref)
        except KeyError:
            return f'<a title="Create note" href="/note?title={element.ref}">{components.get_question_icon()}{element.ref}</a>'
        else:
            return str(components.get_item_link(item))


to_html = marko.Markdown(
    extensions=[
        marko.helpers.MarkoExtension(elements=[Ref], renderer_mixins=[RefRenderer])
    ]
)
