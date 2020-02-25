from lxml import etree

from xml.sax.saxutils import escape

xml_encoding = '<?xml version="1.0" encoding="UTF-8"?>\n'
METADATA_NAMESPACE = "http://soap.sforce.com/2006/04/metadata"


def serialize_xml_for_salesforce(xdoc, xml_declaration=True):
    r = xml_encoding if xml_declaration else ""
    if METADATA_NAMESPACE in xdoc.getroot().tag:
        xdoc.getroot().attrib["xmlns"] = METADATA_NAMESPACE
    for action, elem in etree.iterwalk(
        xdoc, events=("start", "end", "start-ns", "end-ns", "comment")
    ):
        if action == "start-ns":
            prefix, ns = elem
            if ns != METADATA_NAMESPACE:
                raise AssertionError(
                    f"The only namespace that is supported is {METADATA_NAMESPACE}, not {ns}"
                )
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


def has_content(element):
    return element.text or list(element)
