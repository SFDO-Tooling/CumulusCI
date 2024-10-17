"""Salesforce uses a very specialized subset of XML for metadata.
This module has a parser and tree model for dealing with it in
a very Pythonic way.

For example:

>>> from cumulusci.utils.xml.metadata_tree import parse
>>> Recipe = parse("recipe.xml")
>>> print(Recipe.ingredients[0].quantity)

Or to give a more Salesforce-y example:

>>> Package = parse("./cumulusci/files/admin_profile.xml")
>>> print(Package.types[0].members[1].text)
Account
"""

from typing import Generator, Union

from lxml import etree

from . import lxml_parse_file, lxml_parse_string
from .salesforce_encoding import serialize_xml_for_salesforce

METADATA_NAMESPACE = "http://soap.sforce.com/2006/04/metadata"


def parse(source):
    """Parse a file by path or file object into a Metadata Tree

    The parse() function supports any of the following sources:

        * an open file object (make sure to open it in binary mode)
        * a file-like object that has a .read(byte_count) method returning a byte string on each call
        * a filename string or pathlib Path
        * an HTTP or FTP URL string

    """
    if hasattr(source, "open"):  # for pathlib.Path objects
        with source.open(encoding="utf-8") as stream:
            doc = lxml_parse_file(stream)
    else:
        doc = lxml_parse_file(source)
    return MetadataElement(doc.getroot())


def fromstring(source):
    """Parse a Metadata Tree from a string"""
    return MetadataElement(lxml_parse_string(source).getroot())


def parse_package_xml_types(feildName, source_xml_tree):
    """ "Parse metadata types based on the  feildName and map based on the type"""
    xml_map = {}
    for type in source_xml_tree.types:
        members = []
        try:
            for member in type.members:
                members.append(member.text)
        except AttributeError:  # Exception if there are no members for a type
            pass
        xml_map[type[feildName].text] = members
    return xml_map


class MetadataElement:
    '''A class for representing Metadata in a Pythonic tree.

    After you parse into a MetadataElement tree, you can refer
    to child elements like this:

    >>> from cumulusci.utils.xml import metadata_tree
    >>> Package = metadata_tree.fromstring(b"""<?xml version="1.0" encoding="UTF-8"?>
    ... <Package xmlns="http://soap.sforce.com/2006/04/metadata">
    ...     <types>
    ...         <members>CaseReason</members>
    ...         <members>CaseStatus</members>
    ...         <members>CaseType</members>
    ...         <name>StandardValueSet</name>
    ...     </types>
    ...     <version>46.0</version>
    ... </Package>""")
    >>> Package.types.name.text
    'StandardValueSet'

    Or you can refer to them like this:

    >>> Package["types"]["name"].text
    'StandardValueSet'

    That might be convenient if you had the key names in a variable or if you had to refer to an element name
    which would clash with a Python keyword (like `import`) or an instance method (like `text`).

    You can refer to members of lists by index:

    >>> Package["types"]["members"][1]
    <members>CaseStatus</members> element

    There are also methods for finding, appending, inserting and removing nodes, which have their own documentation.
    '''

    __slots__ = ["_element", "_parent", "_ns", "tag"]

    def __init__(self, element: etree._Element, parent: etree._Element = None):
        assert isinstance(element, etree._Element)
        self._element = element
        self._parent = parent
        self._ns = next(iter(element.nsmap.values()))
        self.tag = element.tag.split("}")[1]

    @property
    def text(self):
        if len(self._element):  # if self has any element children
            return self._get_child("text")
        return self._element.text

    @text.setter
    def text(self, text):
        self._element.text = text

    def _wrap_element(self, child: etree._Element):
        return MetadataElement(child, self._element)

    def _add_namespace(self, tag):
        return "{%s}%s" % (self._ns, tag)

    def _get_child(self, childname):
        child_element = self._element.find(self._add_namespace(childname))
        if child_element is None:
            raise AttributeError(f"{childname} not found in {self.tag}")
        return self._wrap_element(child_element)

    def _create_child(self, tag, text=None):
        element = etree.Element(self._add_namespace(tag))
        element.text = text
        return self._wrap_element(element)

    def __getattr__(self, childname):
        return self._get_child(childname)

    def __getitem__(self, item: Union[int, str]):
        """You can get either a child-element by name or a sibling element by index.

        The "sibling element" part may seem non-intuitive but it works like this:

        >>> Recipe = parse("recipe.xml")
        >>> Recipe.ingredients[2]

        First it will evaluate `Recipe.ingredients` and generate an Element for the
        first ingredient.

        Then Python will evaluate the `[2]` and the system will look for the third *sibling*
        of that first ingredient.
        """
        if isinstance(item, int):
            siblings = self._parent.findall(self._element.tag)
            return MetadataElement(siblings[item], self._parent)
        elif isinstance(item, str):
            return self._get_child(item)
        else:
            raise TypeError(
                f"Indices must be integers or strings, not {type(item)}"
            )  # # pragma: no cover

    def append(self, tag: str, text: str = None):
        '''Append a new element at the appropriate place.

        If the parent element (self) already one or more children that match,
        the new element follows the last one.

        Otherwise, the new element goes to the bottom of the parent (self).

        >>> Package = metadata_tree.fromstring(b"""<?xml version="1.0" encoding="UTF-8"?>
        ... <Package xmlns="http://soap.sforce.com/2006/04/metadata">
        ...     <types>
        ...         <members>CaseReason</members>
        ...         <members>CaseStatus</members>
        ...         <members>CaseType</members>
        ...         <name>StandardValueSet</name>
        ...     </types>
        ...     <version>46.0</version>
        ... </Package>""")
        >>> Package.types.append("members", "CaseOfBeer")
        <members>CaseOfBeer</members> element
        >>> print(Package.types.tostring())
        <types xmlns="http://soap.sforce.com/2006/04/metadata">
            <members>CaseReason</members>
            <members>CaseStatus</members>
            <members>CaseType</members>
            <members>CaseOfBeer</members>
            <name>StandardValueSet</name>
        </types>
        '''
        newchild = self._create_child(tag, text)
        same_elements = self._element.findall(self._add_namespace(tag))
        if same_elements:
            last = same_elements[-1]
            index = self._element.index(last)
            self._element.insert(index + 1, newchild._element)
        else:
            self._element.append(newchild._element)
        return newchild

    def insert(self, index: int, tag: str, text: str = None):
        """Insert at a particular index.

        Tag and text can be supplied. Return value is the new element.

        append is preferable because it ensures that nodes are inserted
        in the right "group".

        If you need to get to a particular place in a "group" then insert_before
        and insert_after are preferable.

        If all else fails then you can use this one to precisely insert right
        where you want it but you're responsible for adhering to Salesforce's
        grouping rules.
        """
        newchild = self._create_child(tag, text)
        self._element.insert(index, newchild._element)
        return newchild

    def insert_before(self, oldElement: "MetadataElement", tag: str, text: str = None):
        """Insert before some other element

        Tag and text can be supplied. Return value is the new element."""
        index = self._element.index(oldElement._element)
        return self.insert(index, tag, text)

    def insert_after(self, oldElement: "MetadataElement", tag: str, text: str = None):
        """Insert after some other element

        Tag and text can be supplied. Return value is the new element."""

        index = self._element.index(oldElement._element)
        return self.insert(index + 1, tag, text)

    def remove(self, metadata_element: "MetadataElement") -> None:
        """Remove an element from its parent (self)"""
        self._element.remove(metadata_element._element)

    def find(self, tag, **kwargs):
        """Find a single direct child-elements with name `tag`"""
        return next(self._findall(tag, kwargs), None)

    def findall(self, tag, **kwargs):
        """Find all direct child-elements with name `tag`"""
        return list(self._findall(tag, kwargs))

    def _sub_element_matches_spec(self, e: etree._Element, name: str, value):
        matching_subelement = e.find(self._add_namespace(name))
        if matching_subelement is None and name != "text":
            return value is None
        elif matching_subelement is not None:
            return matching_subelement.text == value
        else:  # matching_subelement is None and name == "text"
            return e.text == value

    def _findall(self, type, kwargs: dict) -> Generator:
        def matches(e):
            return all(
                self._sub_element_matches_spec(e, name, value)
                for name, value in kwargs.items()
            )

        return (
            self._wrap_element(e)
            for e in self._element.findall(self._add_namespace(type))
            if matches(e)
        )

    def tostring(self, xml_declaration=False, include_parent_namespaces=False):
        """Serialize back to XML.

        The XML Declaration is optional and can be controlled by `xml_declaration`"""
        doc = etree.ElementTree(self._element)
        etree.indent(doc, space="    ")
        return serialize_xml_for_salesforce(
            doc,
            xml_declaration=xml_declaration,
            include_parent_namespaces=include_parent_namespaces,
        )

    def __eq__(self, other: "MetadataElement"):
        eq = self._element == other._element
        if eq:
            assert self._parent == other._parent
        return eq

    def __repr__(self):
        children = self._element.getchildren()
        if children:
            contents = f"<!-- {len(children)} children -->"
        elif self.text:
            contents = f"{self.text.strip()}"
        else:
            contents = ""

        return f"<{self.tag}>{contents}</{self.tag}> element"
