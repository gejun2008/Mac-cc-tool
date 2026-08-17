"""Generate minimal OOXML test fixtures with stdlib zipfile only.

The fixtures exercise every detection signal the scanner relies on:
multi-level headers (gridSpan in header rows), row grouping (vMerge),
cross-page header marks (tblHeader), SmartArt/picture graphicData URIs,
and slide flowcharts (cxnSp + flowChart* preset geometry).
"""

import zipfile
from pathlib import Path

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"

_DOCX_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
"""

_DOCX_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""

# One 3-column table: 2 repeated header rows (tblHeader), a 2-wide merged
# header cell (gridSpan), and a vertical merge (vMerge restart + continue).
# Then a SmartArt diagram and a plain picture.
_DOCX_DOCUMENT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{w}" xmlns:a="{a}" xmlns:wp="{wp}">
 <w:body>
  <w:tbl>
   <w:tblGrid><w:gridCol/><w:gridCol/><w:gridCol/></w:tblGrid>
   <w:tr>
    <w:trPr><w:tblHeader/></w:trPr>
    <w:tc><w:tcPr><w:gridSpan w:val="2"/></w:tcPr><w:p/></w:tc>
    <w:tc><w:tcPr><w:vMerge w:val="restart"/></w:tcPr><w:p/></w:tc>
   </w:tr>
   <w:tr>
    <w:trPr><w:tblHeader/></w:trPr>
    <w:tc><w:p/></w:tc>
    <w:tc><w:p/></w:tc>
    <w:tc><w:tcPr><w:vMerge/></w:tcPr><w:p/></w:tc>
   </w:tr>
   <w:tr>
    <w:tc><w:p/></w:tc><w:tc><w:p/></w:tc><w:tc><w:p/></w:tc>
   </w:tr>
  </w:tbl>
  <w:p><w:r><w:drawing><wp:inline>
   <a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/diagram"/></a:graphic>
  </wp:inline></w:drawing></w:r></w:p>
  <w:p><w:r><w:drawing><wp:inline>
   <a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"/></a:graphic>
  </wp:inline></w:drawing></w:r></w:p>
 </w:body>
</w:document>
""".format(w=_W, a=_A, wp=_WP)

_PPTX_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  <Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
</Types>
"""

_PPTX_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>
"""

_PPTX_PRESENTATION = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:p="{p}"/>
""".format(p=_P)

# One slide: two flowchart nodes + one connector (a drawn flowchart), and a
# table with a header-row merge (gridSpan=2 + hMerge continuation).
_PPTX_SLIDE1 = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:p="{p}" xmlns:a="{a}">
 <p:cSld><p:spTree>
  <p:sp><p:spPr><a:prstGeom prst="flowChartProcess"/></p:spPr></p:sp>
  <p:sp><p:spPr><a:prstGeom prst="flowChartDecision"/></p:spPr></p:sp>
  <p:cxnSp><p:spPr><a:prstGeom prst="bentConnector3"/></p:spPr></p:cxnSp>
  <p:graphicFrame>
   <a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table">
    <a:tbl>
     <a:tblPr firstRow="1"/>
     <a:tblGrid><a:gridCol/><a:gridCol/></a:tblGrid>
     <a:tr><a:tc gridSpan="2"><a:txBody/></a:tc><a:tc hMerge="1"><a:txBody/></a:tc></a:tr>
     <a:tr><a:tc><a:txBody/></a:tc><a:tc><a:txBody/></a:tc></a:tr>
    </a:tbl>
   </a:graphicData></a:graphic>
  </p:graphicFrame>
 </p:spTree></p:cSld>
</p:sld>
""".format(p=_P, a=_A)


def build_docx(path):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _DOCX_CONTENT_TYPES)
        zf.writestr("_rels/.rels", _DOCX_RELS)
        zf.writestr("word/document.xml", _DOCX_DOCUMENT)
    return path


def build_pptx(path):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _PPTX_CONTENT_TYPES)
        zf.writestr("_rels/.rels", _PPTX_RELS)
        zf.writestr("ppt/presentation.xml", _PPTX_PRESENTATION)
        zf.writestr("ppt/slides/slide1.xml", _PPTX_SLIDE1)
    return path


def build_all(directory):
    """Build every fixture into directory; return the list of paths."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    return [
        build_docx(directory / "fixture_tables.docx"),
        build_pptx(directory / "fixture_flowchart.pptx"),
    ]


if __name__ == "__main__":
    import sys

    for p in build_all(sys.argv[1] if len(sys.argv) > 1 else "out/fixtures"):
        print(p)
