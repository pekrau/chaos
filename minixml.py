"Minimalist XML library for reading, writing, creating and editing an element tree."

__all__ = ["Element", "read", "parse"]

import copy
import io
import xml.sax
import xml.sax.saxutils


class Element:
    "XML element. Contains a reference to superelement and subelements (if any)."

    REPR_INDENT = 2  # Indentation to use for repr().
    REPR_XML_DECL = True  # repr() outputs XML declaration if the element is root.

    def __init__(self, tag, *subelements, **attrs):
        self.tag = tag
        self.attrs = {}
        for name, value in attrs.items():
            self[name] = value
        self.superelement = None
        self.subelements = []
        for subelement in subelements:
            self.append(subelement)

    def __str__(self):
        "Return the string representation of the element's starting tag."
        outfile = io.StringIO()
        outfile.write(f"<{self.tag}")
        for name, value in self.attrs.items():
            outfile.write(f" {name}={xml.sax.saxutils.quoteattr(value)}")
        if len(self):
            outfile.write(">")
        else:
            outfile.write("/>")
        return outfile.getvalue()

    def __repr__(self):
        "Return the string representation of the element and its subelements."
        outfile = io.StringIO()
        self.write(
            outfile,
            indent=self.REPR_INDENT,
            xml_decl=self.REPR_XML_DECL and self.depth == 0,
        )
        return outfile.getvalue()

    def __getitem__(self, key):
        "Get the value of the attribute in this element."
        try:
            return self.attrs[key]
        except KeyError:
            raise KeyError(f"no such attribute '{key}' in element")

    def __setitem__(self, key, value):
        "Set the value of the attribute in this element."
        if not isinstance(value, str):
            value = str(value)
        self.attrs[key] = value

    def __delitem__(self, key):
        "Delete the attribute in this element."
        try:
            del self.attrs[key]
        except KeyError:
            raise KeyError(f"no such attribute '{key}' in element")

    def __contains__(self, key):
        "Does this element have the given attribute?"
        return key in self.attrs

    def __iter__(self):
        "Iterate over the subelements of this element."
        yield from self.subelements

    def __len__(self):
        "Return the number of subelements of this element."
        return len(self.subelements)

    def __eq__(self, other):
        "Are the element and its subelements equal? Ignores the superelement."
        if not isinstance(other, Element):
            return False
        if self.tag != other.tag:
            return False
        if self.attrs != other.attrs:
            return False
        if len(self) != len(other):
            return False
        for subelement1, subelement2 in zip(self.subelements, other.subelements):
            if subelement1 != subelement2:
                return False
        return True

    def __iadd__(self, other):
        self.append(other)
        return self

    def get(self, key, default=None):
        "Return the value of the given attribute in this element, or the default."
        try:
            return self[key]
        except KeyError:
            return default

    def set(self, key, value):
        "Set the value of the attribute in this element."
        self[key] = value

    @property
    def text(self):
        "Return the text content of this element. All non-blank texts are concatenated."
        result = []
        for subelement in self:
            if isinstance(subelement, str) and subelement.strip():
                result.append(subelement)
        return "".join(result)

    @property
    def superelements(self):
        "List of superelements, most immediate first."
        result = []
        elem = self
        while elem.superelement is not None:
            result.append(elem.superelement)
            elem = elem.superelement
        return result

    @property
    def depth(self):
        "Depth of hierarchy for this element; number of superelements to root."
        result = 0
        elem = self
        while elem.superelement is not None:
            result += 1
            elem = elem.superelement
        return result

    def insert(self, i, elem):
        "Insert the element at position i in the list of subelements of this element."
        assert isinstance(elem, (Element, str))
        if isinstance(elem, Element) and elem.superelement:
            raise ValueError("given element has not been freed from its superelement")
        self.subelements.insert(i, elem)
        if isinstance(elem, Element):
            elem.superelement = self

    def append(self, elem):
        "Append the element last in the subelements of this element."
        assert isinstance(elem, (Element, str))
        if isinstance(elem, Element) and elem.superelement:
            raise ValueError("given element has not been freed from its superelement")
        self.subelements.append(elem)
        if isinstance(elem, Element):
            elem.superelement = self

    def free(self):
        "Remove this element from its superelement, if any."
        self.superelement = None

    def create(self, tag, **attrs):
        """Create an element with the given tag and attributes,
        and append to the subelements of this element.
        Return the created element.
        """
        elem = Element(tag, **attrs)
        self.append(elem)
        return elem

    def copy(self):
        """Make a copy of this element and its subelements (i.e. deepcopy).
        The returned element copy has no superelement.
        """
        result = copy.deepcopy(self)
        result.superelement = None
        result._set_superelement()
        return result

    def _set_superelement(self):
        "Set the correct superelement for all subelements recursively."
        for subelement in self:
            if isinstance(subelement, Element):
                subelement.superelement = self
                subelement._set_superelement()

    def walk(self, test=None):
        """Walk over this element and all its subelements recursively,
        yielding those elements that match the given test function.
        If no test function given, yield all.
        """
        if test is None or test(self):
            yield self
        for subelement in self:
            if not isinstance(subelement, Element):
                continue
            yield from subelement.walk(test=test)

    def diff(self, other):
        "Return the first difference between this element and the other, recursively."
        if not isinstance(other, Element):
            return ("instance", self, other)
        if self.tag != other.tag:
            return ("tag", self, other)
        if self.attrs != other.attrs:
            return ("attrs", self, other)
        if len(self) != len(other):
            return ("len", self, other)
        for subelement1, subelement2 in zip(self.subelements, other.subelements):
            if isinstance(subelement1, Element):
                if result := subelement1.diff(subelement2):
                    return result
            elif subelement1 != subelement2:
                return ("diff", subelement1, subelement2)

    def write(self, outfile, indent=None, xml_decl=False, encoding="utf-8"):
        "Write the XML of the element and its subelements into the open file object."
        assert indent is None or isinstance(indent, int)
        if xml_decl:
            outfile.write(f'<?xml version="1.0" encoding="{encoding}"?>\n')
        if indent is None:
            padding = ""
        else:
            padding = " " * indent * self.depth
        outfile.write(padding)
        outfile.write(f"<{self.tag}")
        for name, value in self.attrs.items():
            outfile.write(f" {name}={xml.sax.saxutils.quoteattr(value)}")
        if len(self):
            outfile.write(">")
            newline = False
            for elem in self:
                if isinstance(elem, Element):
                    if indent:
                        outfile.write("\n")
                    elem.write(outfile, indent=indent)
                    newline = True
                elif isinstance(elem, str):
                    outfile.write(xml.sax.saxutils.escape(elem))
                    newline = False
                else:
                    outfile.write(xml.sax.saxutils.escape(str(elem)))
                    newline = False
            if newline:
                if indent:
                    outfile.write("\n")
                outfile.write(padding)
            outfile.write(f"</{self.tag}>")
        else:
            outfile.write(" />")


class ContentHandler(xml.sax.ContentHandler):
    "Parse XML read events into Element tree."

    def __init__(self):
        self.stack = []
        self.root = None

    def startElement(self, tag, attrs):
        elem = Element(tag, **dict(attrs))
        if self.stack:
            self.stack[-1].subelements.append(elem)
            elem.superelement = self.stack[-1]
        else:
            self.root = elem
        self.stack.append(elem)

    def endElement(self, tag: str):
        self.stack.pop()

    def characters(self, content: str):
        if content.strip():
            self.stack[-1].subelements.append(xml.sax.saxutils.unescape(content))


def read(filepath_or_stream):
    """Read and parse the file given by its path, or the open file object.
    Returns the root XML element.
    """
    try:
        content_handler = ContentHandler()
        xml.sax.parse(filepath_or_stream, content_handler)
    except xml.sax.SAXException as error:
        raise ValueError(f"XML parse error: {error}")
    return content_handler.root


def parse(content):
    "Parse the given XML content (string). Return the root XML element."
    return read(io.StringIO(content))


if __name__ == "__main__":
    original = parse("""<?xml version="1.0" encoding="UTF-8" ?>
<package xmlns="http://www.idpf.org/2007/opf" xmlns:dc="http://purl.org/dc/elements/1.1/" unique-identifier="db-id" version="3.0">
<metadata>
<dc:title id="t1">Sample .epub Book</dc:title>
<dc:creator id="creator">Thomas Hansen</dc:creator>
<dc:identifier id="db-id">isbn</dc:identifier>
<meta property="dcterms:modified">2014-03-27T09:14:09Z</meta>
<dc:language>en</dc:language>
</metadata>
</package>""")
    output = io.StringIO()
    original.write(output, indent=2)
    print(output.getvalue())

    root = Element("package", xmlns="http://www.idpf.org/2007/opf", version="3.0")
    root["xmlns:dc"] = "http://purl.org/dc/elements/1.1/"
    root["unique-identifier"] = "db-id"
    metadata = root.create("metadata")
    metadata.create("dc:title", id="t1").append("Sample .epub Book")
    metadata.create("dc:creator", id="creator").append("Thomas Hansen")
    metadata.create("dc:identifier", id="db-id").append("isbn")
    metadata.create("meta", property="dcterms:modified").append("2014-03-27T09:14:09Z")
    metadata.create("dc:language").append("en")
    output = io.StringIO()
    root.write(output, indent=2)
    print(output.getvalue())

    if diff := original.diff(root):
        print(diff)
