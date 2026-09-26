"Extensions to Markdown."

import csv
import io
import html
import string

import marko
import marko.inline
import marko.helpers
import mermaidx

import components
import constants
import items


class Url(marko.inline.InlineElement):
    "Extension to make a bare URL into a link."

    pattern = constants.URL
    parse_children = False

    def __init__(self, match):
        self.url = match.group(1)


class UrlRenderer:
    "Output a link to the bare URL."

    def render_url(self, element):
        return f'<a href="{element.url}">{element.url}</a>'


class Email(marko.inline.InlineElement):
    "Extension to make a bare email into a link."

    pattern = constants.EMAIL
    parse_children = False

    def __init__(self, match):
        self.email = match.group(1)


class EmailRenderer:
    "Output a link to the bare email."

    def render_email(self, element):
        return f'<a href="mailto:{element.email}">{element.email}</a>'


class Tel(marko.inline.InlineElement):
    "Extension to make a bare telephone number into a link."

    pattern = constants.TEL
    parse_children = False

    def __init__(self, match):
        self.tel = match.group(1)


class TelRenderer:
    "Output a link to the bare telephone number."

    def render_tel(self, element):
        clean = "".join([n for n in element.tel if n in string.digits])
        if element.tel.startswith("+"):
            clean = "+" + clean
        return f'<a href="tel:{clean}">{element.tel}</a>'


class Reference(marko.inline.InlineElement):
    "Extension for a cross-referenced item."

    pattern = constants.REFERENCE
    parse_children = False

    def __init__(self, match):
        self.reference = match.group(1)


class ReferenceRenderer:
    "Output a link to the cross-referenced item."

    def render_reference(self, element):
        try:
            item = items.get(element.reference)
        except KeyError:
            return f'<span class="error">Error: no such item [[{element.reference}]]</span>'
        return str(components.get_item_link(item))


class Include(marko.inline.InlineElement):
    "Extension for an included item."

    pattern = constants.INCLUDE
    parse_children = False

    def __init__(self, match):
        self.include = match.group(1)


class IncludeRenderer:
    "Include the content of the item."

    def render_include(self, element):
        try:
            item = items.get(element.include)
        except KeyError:
            return f'<span class="error">Error: no such item [!{element.include}]]</span>'

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
                        result.append(
                            f'<div class="overflow-auto"><div id="chaos_graphic{ordinal}"></div></div>'
                        )
                        result.append(
                            f"""<script>const specification = {item.specification};
vegaEmbed("#chaos_graphic{ordinal}", specification, {{downloadFileName: "filename"}})
.then(result=>console.log(result))
.catch(console.warn);
</script>"""
                        )
                        return "\n".join(result)

                return (
                    f'<span class="error">Error: not implemented [!{item.id}]]</span>'
                )

        return f'<span class="error">Error: invalid type [!{item.id}]]</span>'


class FencedCodeRenderer:
    """Handle fenced code according to language, if specified.
    - 'table-csv': read content as CSV and format in a table.
    """

    def render_fenced_code(self, element):
        content = element.children[0].children
        match element.lang:
            case "table-csv":
                if "striped" in element.extra:
                    result = ['<table class="striped">']
                else:
                    result = ["<table>"]
                inputfile = io.StringIO(content)
                reader = csv.reader(inputfile)
                result.extend(["<tr>", "<thead>"])
                for cell in next(reader):
                    result.append(f"<th>{cell}</th>")
                result.extend(["</tr>", "</thead>", "<tbody>"])
                for row in reader:
                    result.append("<tr>")
                    for cell in row:
                        try:
                            float(cell)
                            result.append(f'<td class="right">{cell}</td>')
                        except (ValueError, TypeError):
                            result.append(f'<td>{cell}</td>')
                    result.append("</tr>")
                result.extend(["</tbody>", "</table>"])
                return "".join(result)
            case "mermaid":
                return mermaidx.render(content).svg()
            case _:
                return "<pre><code>{}</code></pre>\n".format(html.escape(content))


def to_html(text):
    "Use a fresh converter instance for each invocation."
    if not text:
        return ""
    converter = marko.Markdown(
        extensions=[
            marko.helpers.MarkoExtension(
                elements=[Url, Email, Tel, Reference, Include],
                renderer_mixins=[
                    UrlRenderer,
                    EmailRenderer,
                    TelRenderer,
                    ReferenceRenderer,
                    IncludeRenderer,
                    FencedCodeRenderer,
                ],
            )
        ]
    )
    return converter(text)
