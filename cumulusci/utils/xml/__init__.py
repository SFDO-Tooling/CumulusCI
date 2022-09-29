import typing as T
import xml.etree.ElementTree as etree
from pathlib import Path

from lxml import etree as lxml_etree

UTF8 = "UTF-8"


def elementtree_parse_file(path: T.Union[str, Path, T.IO]) -> etree.ElementTree:
    """Parse a file from filename, Path or Stream using Python stdlib.

    All else equal, prefer elementtree over LXML for performance and simplicity reasons."""
    try:
        tree = etree.parse(path)
    except etree.ParseError as err:
        err.filename = path
        raise err
    return tree


def lxml_parse_file(path: T.Union[str, Path, T.IO]) -> lxml_etree._ElementTree:
    """Parse a file from filename, Path or stream using lxml for richer API

    Use this if you need advanced xpath and parent-pointer features.
    Otherwise prefer elementree_parse_file for performance and simplicity reasons."""
    parser = lxml_etree.XMLParser(
        resolve_entities=False, load_dtd=False, no_network=True
    )
    try:
        if isinstance(path, Path):
            path = str(path)
        tree = lxml_etree.parse(path, parser=parser)
    except etree.ParseError as err:
        err.filename = path
        raise err
    return tree


elementtree_parse_string = etree.fromstring


def lxml_parse_string(string: str) -> lxml_etree._ElementTree:
    """Parse a string using lxml for richer API

    Use this if you need advanced xpath and parent-pointer features.
    Otherwise prefer elementree_parse_string for performance and simplicity reasons."""

    parser = lxml_etree.XMLParser(
        resolve_entities=False, load_dtd=False, no_network=True
    )
    return lxml_etree.ElementTree(lxml_etree.fromstring(string, parser=parser))


def remove_xml_element_file(name: str, path: T.Union[str, Path]):
    """Remove XML elements from a single file"""
    etree.register_namespace("", "http://soap.sforce.com/2006/04/metadata")
    tree = elementtree_parse_file(path)
    tree = remove_xml_element(name, tree)
    return tree.write(path, encoding=UTF8, xml_declaration=True)


def remove_xml_element_string(name: str, content: str):
    """Remove XML elements from a string"""
    etree.register_namespace("", "http://soap.sforce.com/2006/04/metadata")
    tree = etree.fromstring(content)
    tree = remove_xml_element(name, tree)
    clean_content = etree.tostring(tree, encoding=UTF8)
    return clean_content


def remove_xml_element(name: str, tree):
    """Removes XML elements from an ElementTree content tree"""
    # root = tree.getroot()
    remove = tree.findall(
        ".//{{http://soap.sforce.com/2006/04/metadata}}{}".format(name)
    )
    if not remove:
        return tree

    parent_map = {c: p for p in tree.iter() for c in p}

    for elem in remove:
        parent = parent_map[elem]
        parent.remove(elem)

    return tree
