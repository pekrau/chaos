"Extension to Markdown; xref."

import marko
import marko.inline
import marko.helpers

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
            return f'<mark><a href="{item.url}">{item.title}</a></mark>'
        except KeyError:
            return f'<s>[[{element.xref}]]</s>'


to_html = marko.Markdown(
    extensions=[
        marko.helpers.MarkoExtension(elements=[Xref], renderer_mixins=[XrefRenderer])
    ]
)
