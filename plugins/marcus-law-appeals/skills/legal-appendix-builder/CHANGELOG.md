# Changelog

## v3.0.0 - Word fidelity + AI typography ban (2026-05-09)

### New scripts
- **sanitize_text.py** - central guard against AI-giveaway typography.
  Replaces em dash (U+2014), en dash (U+2013), figure dash, horizontal bar,
  two-em dash, three-em dash with hyphen-minus. Optional smart-quote
  replacement. Used wherever Claude writes a string into the package.
- **prepare_docx.py** - pre-process pleading DOCX before conversion.
  Applies 1.5 line spacing to body paragraphs, 1.15 line spacing + zero
  before/after to all paragraphs in tables, and sanitises em dashes inside
  the document text (preserves run-level formatting). Recurses into
  nested tables.
- **install_fonts.py** - copies user-supplied Word .ttf files
  (David, Times New Roman, Arial, etc.) into ~/.fonts and refreshes
  fc-cache. Without these fonts, LibreOffice silently substitutes
  DejaVu Sans for Hebrew body text, breaking the visual identity of any
  Israeli legal document.

### Modified scripts
- **bind_pdf.py**
  - DOCX-to-PDF now uses LibreOffice headless (with installed Word fonts)
    as the primary path. Pandoc + WeasyPrint remains a fallback. Reason:
    LibreOffice respects Word paragraph properties (line spacing, run
    formatting); WeasyPrint, being HTML-based, throws those away.
  - New parameter prefer_sibling_pdf=True (default). If you call
    bind_pleading('X.docx', ...) and X.pdf exists in the same folder,
    the PDF is used instead - preserves the user's manual Word export.
  - Every appendix list passes through sanitize_appendix_list() on entry.
  - Bookmark labels and TOC label sanitised via sanitize().
- **create_toc.py**
  - Header changed from a Hebrew title with em dash to one with hyphen.
  - Simple-mode rows now use ":" instead of em dash.
- **create_cover_pages.py**
  - Sample data switched to plain hyphens.

### Iron Rules
- **Iron Rule 3 (NEW)** - No em dashes in Claude-generated chrome.
- **Iron Rule 4 (NEW)** - Prefer sibling PDF over DOCX conversion.

### New dependencies
- python-docx is now required (was previously optional, only used by legal-docx).

## v2.0.0 - RTL fixes (2026-05-09)
Three components rewritten to fix Hebrew RTL rendering bugs:
- create_toc.py: WeasyPrint instead of reportlab+bidi
- create_cover_pages.py: WeasyPrint with corrected layout
- bind_pdf.py: PyMuPDF for merge + page numbers (respects coordinate systems)
