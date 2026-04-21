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
            return f'<span class="error">[!{element.ref}]] no such item</span>'
        return str(components.get_item_link(item))


class Incl(marko.inline.InlineElement):
    "Markdown extension for an included item."

    pattern = constants.INCL
    parse_children = False

    def __init__(self, match):
        self.incl = match.group(1)


class InclRenderer:
    "Include the content of the item."

    def render_incl(self, element):
        try:
            item = items.get(element.incl)
        except KeyError:
            return f'<span class="error">Error: no such item [!{element.incl}]]</span>'

        match item.type:

            case "link":
                return f'<a href="{item.href}" target="_blank">{item.title}</a>'

            case "image":
                return f'<img src="{item.url_file}" title="{item}">'

            case "graphic":

                match item.graphic:

                    case "SVG":
                        return item.specification

                    case "Vega-Lite":
                        result = []
                        try:
                            self._vega_lite_ordinal += 1
                            ordinal = self._vega_lite_ordinal
                        except AttributeError:
                            ordinal = self._vega_lite_ordinal = 1
                            # Add Vega-Lite libraries only for the first instance.
                            result.extend(
                                [
                                    f'<script src="{lib}"></script>'
                                    for lib in constants.VEGA_LITE_LIBRARIES
                                ]
                            )
                        result.append(f'<div class="overflow-auto"><div id="chaos_graphic{ordinal}"></div></div>')
                        result.append(
                            f"""<script>const specification = {item.specification};
vegaEmbed("#chaos_graphic{ordinal}", specification, {{downloadFileName: "filename"}})
.then(result=>console.log(result))
.catch(console.warn);
</script>"""
                        )
                        return "\n".join(result)

                    case _:
                        return f'<span class="error">Error: not implemented [!{item.id}]]</span>'

            case _:
                return f'<span class="error">Error: invalid type [!{item.id}]]</span>'


def to_html(text):
    "Use a fresh converter instance for each invocation."
    converter = marko.Markdown(
        extensions=[
            marko.helpers.MarkoExtension(
                elements=[Ref, Incl], renderer_mixins=[RefRenderer, InclRenderer]
            )
        ]
    )
    return converter(text)
