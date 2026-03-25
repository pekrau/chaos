"Extension to Markdown; xref."

import marko
import marko.inline
import marko.helpers

import components
import constants
import items


class Xref(marko.inline.InlineElement):
    "Markdown extension for a cross-referenced item."

    pattern = constants.XREF
    parse_children = False

    def __init__(self, match):
        self.xref = match.group(1)


class XrefRenderer:
    "Output a link to the cross-referenced item."

    def render_xref(self, element):
        try:
            item = items.get(element.xref)
        except KeyError:
            return f'<mark><a title="Create tag" href="/tag?title={element.xref}">{components.get_question_icon()}{element.xref}</a></mark>'
        else:
            return f"<mark>{components.get_item_link(item)}</mark>"


to_html = marko.Markdown(
    extensions=[
        marko.helpers.MarkoExtension(elements=[Xref], renderer_mixins=[XrefRenderer])
    ]
)
