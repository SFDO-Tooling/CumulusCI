from lxml import etree

from xml.sax.saxutils import escape

xml_encoding = '<?xml version="1.0" encoding="UTF-8"?>\n'
METADATA_NAMESPACE = "http://soap.sforce.com/2006/04/metadata"
_supported_events = ("start", "end", "start-ns", "end-ns", "comment")


def serialize_xml_for_salesforce(xdoc, xml_declaration=True):
    r = xml_encoding if xml_declaration else ""

    new_namespace_declarations = {}
    all_namespaces = {}

    for action, elem in etree.iterwalk(xdoc, events=_supported_events):
        if action == "start-ns":
            prefix, ns = elem
            new_namespace_declarations[prefix] = ns
            all_namespaces[ns] = prefix
        elif action == "start":
            tag = elem.tag
            if "}" in tag:
                tag = _render_name(tag, all_namespaces)
            text = (
                escape(elem.text, {"'": "&apos;", '"': "&quot;"})
                if elem.text is not None
                else ""
            )
            ns = (
                _render_ns_declarations(new_namespace_declarations)
                if new_namespace_declarations
                else ""
            )
            new_namespace_declarations = {}

            attrs = "".join(
                [
                    f' {_render_attr_name(k, all_namespaces)}="{v}"'
                    for k, v in elem.attrib.items()
                ]
            )
            if not _has_content(elem):
                r += f"<{tag}{ns}{attrs}/>"
            else:
                r += f"<{tag}{ns}{attrs}>{text}"
        elif action == "end":
            if _has_content(elem):
                tag = elem.tag
                if "}" in tag:
                    tag = tag.split("}")[1]
                r += f"</{tag}>"
            tail = elem.tail if elem.tail else "\n"
            r += tail
        elif action == "comment":
            r += str(elem) + (elem.tail if elem.tail else "")
    return r


def _has_content(element):
    return element.text or list(element)


def _render_ns_declarations(declarations):
    def format_ns(prefix, url):
        return (f":{prefix}" if prefix else "") + f'="{url}"'

    return "".join(
        f" xmlns{format_ns(prefix, url)}" for prefix, url in declarations.items()
    )


def _render_attr_name(name, namespaces):
    if name[0] == "{":
        return _render_name(name, namespaces)
    else:
        return name


def _render_name(name, namespaces):
    assert name[0] == "{"
    url, name = name[1:].split("}")
    prefix = namespaces[url]

    if prefix:
        return f"{prefix}:{name}"
    else:
        return name
