#!/usr/bin/env python3
"""Extract plain text from a .docx brief so the model can read it.

Usage:
    python read_docx.py <brief.docx>

Prints the document text to stdout (paragraphs and table cells, in order).
PDF and .txt/.md briefs do NOT need this — read those with the Read tool
directly (Read parses PDFs natively).
"""
import sys

try:
    from docx import Document
    from docx.document import Document as _Doc
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import Table
    from docx.text.paragraph import Paragraph
except ImportError:
    sys.stderr.write("python-docx is required: pip install python-docx\n")
    sys.exit(2)


def _iter_block_text(parent):
    """Yield paragraph text in document order, including inside tables."""
    body = parent.element.body
    for child in body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent).text
        elif isinstance(child, CT_Tbl):
            table = Table(child, parent)
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells]
                yield " | ".join(c for c in cells if c)


def main():
    if len(sys.argv) != 2:
        sys.stderr.write(__doc__)
        sys.exit(1)
    doc = Document(sys.argv[1])
    for line in _iter_block_text(doc):
        print(line)


if __name__ == "__main__":
    main()
