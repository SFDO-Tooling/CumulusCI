import os
import fnmatch
from xml.sax.saxutils import escape


import lxml.etree as ET
from xml.etree.ElementTree import ParseError


UTF8 = "UTF-8"
XML_ENCODING_DECL = '<?xml version="1.0" encoding="UTF-8"?>\n'


def elementtree_parse_file(path: str):
    try:
        tree = ET.parse(path)
    except (ET.ParseError, ParseError) as err:
        err.filename = path
        print("XXXX", type(err), err)
        raise err
    except Exception as err:
        print("XXXX", type(err), err)
        raise
    return tree


def serialize_sf_style(etree_doc):
    """Salesforce XML files have some idiosyncracies that this serializer supports

    Salesforce encodes ' as &apos; and " and &quot;"""
    r = XML_ENCODING_DECL
    etree_doc.getroot().attrib["xmlns"] = "http://soap.sforce.com/2006/04/metadata"
    for action, elem in ET.iterwalk(
        etree_doc, events=("start", "end", "start-ns", "end-ns", "comment")
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
            r += f"<{tag}{attrs}>{text}"
        elif action == "end":
            tag = elem.tag
            if "}" in tag:
                tag = tag.split("}")[1]
            tail = elem.tail if elem.tail else "\n"
            r += f"</{tag}>{tail}"
        elif action == "comment":
            r += str(elem) + (elem.tail if elem.tail else "")
    return r


def removeXmlElement(name, directory, file_pattern, logger=None):
    """ Recursively walk a directory and remove XML elements """
    for path, dirs, files in os.walk(os.path.abspath(directory)):
        for filename in fnmatch.filter(files, file_pattern):
            filepath = os.path.join(path, filename)
            remove_xml_element_file(name, filepath)


def remove_xml_element_file(name, path):
    """ Remove XML elements from a single file """
    # ET.register_namespace("", "http://soap.sforce.com/2006/04/metadata")
    tree = elementtree_parse_file(path)
    tree = remove_xml_element(name, tree)
    return tree.write(path, encoding=UTF8, xml_declaration=True)


def remove_xml_element_string(name, content):
    """ Remove XML elements from a string """
    # ET.register_namespace("", "http://soap.sforce.com/2006/04/metadata")
    tree = ET.fromstring(content)
    tree = remove_xml_element(name, tree)
    clean_content = ET.tostring(tree, encoding=UTF8)
    return clean_content


def remove_xml_element(name, tree):
    """ Removes XML elements from an ElementTree content tree """
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
