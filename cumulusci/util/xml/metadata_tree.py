from typing import Sequence, Union

from lxml import etree
from xml.sax.saxutils import escape

xml_encoding = '<?xml version="1.0" encoding="UTF-8"?>\n'
METADATA_NAMESPACE = "http://soap.sforce.com/2006/04/metadata"


def _add_namespace(tag):
    return "{%s}%s" % (METADATA_NAMESPACE, tag)


def parse(source):
    doc = etree.parse(source)
    return MetadataElement(doc.getroot(), doc=doc)


def fromstring(source):
    return MetadataElement(etree.fromstring(source))


class MetadataElement:
    __slots__ = ["_element", "_parent", "_doc", "tag"]

    def __init__(
        self,
        element: etree._Element,
        parent: etree._Element = None,
        doc: etree._ElementTree = None,
    ):
        assert isinstance(element, etree._Element)
        self._element = element
        self._parent = parent
        self._doc = doc
        self.tag = element.tag.split("}")[1]

    @property
    def text(self):
        if len(self._element):
            return self._wrap_element(self._element.find(_add_namespace("text")))
        else:
            return self._element.text

    def _wrap_element(self, child: etree._Element):
        return MetadataElement(child, self._element)

    @text.setter
    def text(self, text):
        self._element.text = text

    def _get_child(self, childname):
        child_element = self._element.find(_add_namespace(childname))
        if child_element is None:
            raise AttributeError(f"{childname} not found in {self.tag}")
        return self._wrap_element(child_element)

    def _create_child(self, tag, text=None):
        element = etree.Element(_add_namespace(tag))
        element.text = text
        return self._wrap_element(element)

    def __getattr__(self, childname):
        return self._get_child(childname)

    def __getitem__(self, item: Union[int, str]):
        if isinstance(item, int):
            children = self._parent.findall(self._element.tag)
            return self._wrap_element(children[item])
        elif isinstance(item, str):
            return self._get_child(item)

    def append(self, tag: str, text: str = None):
        newchild = self._create_child(tag, text)
        same_elements = self._element.findall(self._element.tag)
        if same_elements:
            last = same_elements[-1]
            self._element.insert(last.index() + 1, newchild._element)
        else:
            self._element.append(newchild._element)
        return newchild

    def insert(self, index: int, tag: str, text: str = None):
        newchild = self._create_child(tag, text)
        self._element.insert(index, newchild._element)
        return newchild

    def insertBefore(self, oldElement: "MetadataElement", tag: str, text: str = None):
        index = self._element.index(oldElement._element)
        newchild = self._create_child(tag, text)
        self._element.insert(index, newchild._element)
        return newchild

    def insertAfter(self, oldElement: "MetadataElement", tag: str, text: str = None):
        index = self._element.index(oldElement._element)
        newchild = self._create_child(tag, text)
        self._element.insert(index + 1, newchild._element)
        return newchild

    def extend(self, iterable: Sequence):
        self._element.extend(newchild._element for newchild in iterable)

    def remove(self, metadata_element):
        self._element.remove(metadata_element._element)

    def find(self, tag, text=None):
        return next(self._findall(tag, text), None)

    def findall(self, tag, text=None):
        return list(self._findall(tag, text))

    def _findall(self, type, text=None):
        def matches(e):
            if text:
                return e.text == text
            else:
                return True

        return (
            self._wrap_element(e)
            for e in self._element.findall(_add_namespace(type))
            if matches(e)
        )

    def tostring(self):
        if self._doc:
            etree.indent(self._doc, space="    ")
            return salesforce_encoding(self._doc)
        else:
            return etree.tostring(self._element, encoding="unicode", pretty_print=True)

    def __eq__(self, other: "MetadataElement"):
        return self._element == other._element

    def __repr__(self):
        return f"<{self.tag}>{self.text}</{self.tag}> element"


def has_content(element):
    return element.text or list(element)


def salesforce_encoding(xdoc):
    r = xml_encoding
    if METADATA_NAMESPACE in xdoc.getroot().tag:
        xdoc.getroot().attrib["xmlns"] = METADATA_NAMESPACE
    for action, elem in etree.iterwalk(
        xdoc, events=("start", "end", "start-ns", "end-ns", "comment")
    ):
        if action == "start-ns":
            pass  # handle this nicely if SF starts using multiple namespaces
        elif action == "start":
            tag = elem.tag
            if "}" in tag:
                tag = tag.split("}")[1]
            text = (
                escape(elem.text, {"'": "&apos;", '"': "&quot;"})
                if elem.text is not None
                else ""
            )

            attrs = "".join([f' {k}="{v}"' for k, v in elem.attrib.items()])
            if not has_content(elem):
                r += f"<{tag}{attrs}/>"
            else:
                r += f"<{tag}{attrs}>{text}"
        elif action == "end" and has_content(elem):
            tag = elem.tag
            if "}" in tag:
                tag = tag.split("}")[1]
            tail = elem.tail if elem.tail else "\n"
            r += f"</{tag}>{tail}"
        elif action == "comment":
            r += str(elem) + (elem.tail if elem.tail else "")
    return r
