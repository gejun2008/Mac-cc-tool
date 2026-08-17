"""Shared OOXML namespaces and zip/XML helpers. Stdlib only, fully deterministic."""

import zipfile
from xml.etree import ElementTree as ET

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}

# a:graphicData/@uri -> object kind. This is the authoritative signal for what a
# "figure" really is inside native Office files (design decision: OOXML direct
# read is the upper bound for diagrams, OCR the lower bound).
_GRAPHIC_URI_KIND = {
    "http://schemas.openxmlformats.org/drawingml/2006/picture": "picture",
    "http://schemas.openxmlformats.org/drawingml/2006/chart": "chart",
    "http://schemas.microsoft.com/office/drawing/2014/chartex": "chart",
    "http://schemas.openxmlformats.org/drawingml/2006/diagram": "smartart",
    "http://schemas.openxmlformats.org/drawingml/2006/ole": "embedded",
    "http://schemas.openxmlformats.org/drawingml/2006/table": "table_frame",
    "http://schemas.microsoft.com/office/word/2010/wordprocessingShape": "shape",
    "http://schemas.microsoft.com/office/word/2010/wordprocessingGroup": "shape_group",
    "http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas": "shape_group",
}


def qn(prefix, tag):
    """Return the fully-qualified {namespace}tag name for ElementTree."""
    return "{%s}%s" % (NS[prefix], tag)


def load_xml(zf, name):
    """Parse one XML part from an open ZipFile and return its root element."""
    with zf.open(name) as fh:
        return ET.parse(fh).getroot()


def classify_graphic_uri(uri):
    """Map a graphicData URI to an object kind; unknown URIs become 'other'."""
    if not uri:
        return "other"
    return _GRAPHIC_URI_KIND.get(uri, "other")


def flag_on(elem, val_attr):
    """True when an OOXML boolean element is present and not explicitly off.

    OOXML convention: presence of the element means true unless its val
    attribute says otherwise (e.g. <w:tblHeader w:val="false"/>).
    """
    if elem is None:
        return False
    return elem.get(val_attr, "true") not in ("0", "false", "off", "none")
