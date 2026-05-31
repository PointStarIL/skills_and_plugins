---
name: build-appendix-pdf
description: "מארגן, ממספר וכורך נספחים של כתבי בי-דין ל-PDF מוכן להגשה לבית המשפט: מספור עברי/ערבי, אימות הפניות צולבות מול גוף כתב הטענות, דפי כיסוי, תוכן עניינים וסימניות. ממיר DOCX ל-PDF תוך שמירת עיצוב Word (פונטים מצורפים), אוכף מרווח 1.5 בגוף ו-1.15 בטבלאות, מנקה מקף ארוך, ומתקן כיוון עמוד. הפעל כאשר: 'כרוך נספחים', 'נספחים', 'דפי כיסוי', 'אימות הפניות', 'bind appendices', 'appendix package'."
version: "3.2.0"
---

# build-appendix-pdf (v3.1)

## Soul
I organize, number, and bind legal pleading appendices into court-ready PDFs. I manage Hebrew and Arabic numbering styles, validate cross-references against the pleading text, and produce professional court documents with complete metadata tracking. I enforce **five Iron Rules** that guarantee the output is correctly oriented, properly rendered, formatted to match a human-typed Word document, free of AI-giveaway typography, and rendered with the right Word fonts on any machine.

## What's new in v3.1

A `fonts/` folder ships inside the skill containing the user's licensed Microsoft Word TTFs (David, Times New Roman, Arial). On first run on any machine, `ensure_fonts_installed()` auto-copies them to `~/.fonts` and refreshes `fc-cache`. Subsequent runs are no-ops. Result: the skill is fully portable - drop the folder onto a fresh Linux sandbox and binding works without any manual setup.

## What was new in v3.0

| Area | v2 | v3 |
|------|----|----|
| DOCX conversion | Pandoc + WeasyPrint primary | LibreOffice primary (uses David/Times/Arial fonts); WeasyPrint fallback. LibreOffice + Word fonts produces a near-identical match to the user's manual Word export. |
| Em dashes (`—`) | Could leak into TOC, covers, bookmarks | **Banned everywhere**. `sanitize_text.sanitize()` replaces every U+2014/U+2013 with `-`. |
| Line spacing | Inherited from DOCX | `prepare_docx.py` applies **1.5 lines for body**, **1.15 lines for table cells** with `space_before=0`/`space_after=0`. |
| Sibling PDF detection | Not supported | `bind_pleading(prefer_sibling_pdf=True)` automatically uses `<stem>.pdf` if it exists alongside the DOCX. |
| Word fonts | Manual install | Bundled in `fonts/` folder, auto-installed on first run. |

## Iron Rules

### Iron Rule 1 - DOCX must be converted to PDF
LibreOffice headless (with installed Word fonts) is primary. WeasyPrint is fallback. Detection via magic bytes, not extension.

### Iron Rule 2 - Orientation must be detected and fixed
Tesseract OSD on every image-based page; auto-rotate 90°/180°/270°.

### Iron Rule 3 - No em dashes in Claude-generated chrome
Every TOC header, TOC row, cover-page name, bookmark label, and metadata string passes through `sanitize_text.sanitize()`. Em dashes (U+2014) and en dashes (U+2013) are replaced with hyphen-minus.

### Iron Rule 4 - Prefer sibling PDF over DOCX conversion
When `bind_pleading('X.docx', ..., prefer_sibling_pdf=True)` and `X.pdf` exists in the same directory, the PDF is used (preserves the user's manual Word export).

### Iron Rule 5 - Word fonts ensured on every run (NEW v3.1)
Before every binding, `ensure_fonts_installed()` checks fontconfig for David / Times New Roman / Arial. If missing, copies bundled TTFs from `<skill>/fonts/` into `~/.fonts` and refreshes `fc-cache`. No-op when fonts are already installed. Skill is fully portable across machines.

## Folder Layout

```
build-appendix-pdf/
├── SKILL.md
├── INSTALL.md
├── CHANGELOG.md
├── fonts/                  <-- NEW v3.1
│   ├── README.md           licensing notice
│   ├── david.ttf, davidbd.ttf
│   ├── times.ttf, timesbd.ttf, timesi.ttf, timesbi.ttf
│   ├── arial.ttf, arialbd.ttf, ariali.ttf, arialbi.ttf, ariblk.ttf
│   └── ARIALN*.TTF, ARLRDBD.TTF
├── references/
│   └── patterns-extracted.md
└── scripts/
    ├── bind_pdf.py         master entrypoint (calls ensure_fonts_installed)
    ├── prepare_docx.py     1.5/1.15 line spacing + dash strip
    ├── sanitize_text.py    em-dash / en-dash guard
    ├── install_fonts.py    auto-install from bundled fonts/
    ├── create_toc.py       WeasyPrint TOC
    ├── create_cover_pages.py  WeasyPrint covers
    ├── convert_docx.py     Pandoc + WeasyPrint fallback
    ├── fix_orientation.py  Tesseract OSD
    ├── compress_pdf.py     Ghostscript compression
    ├── redact_pdf.py       redaction with Human Gate
    ├── hebrew_utils.py     Hebrew letter conversion
    └── validate_references.py
```

## Workflow

```python
from prepare_docx import prepare_pleading
from bind_pdf import bind_pleading

# 1. Apply 1.5 body / 1.15 table line spacing + sanitise dashes in DOCX
prepare_pleading('pleading.docx', '/tmp/spaced.docx')

# 2. Bind. Auto-installs fonts on first run, sanitises appendix names,
#    prefers sibling PDF if it exists.
result = bind_pleading(
    pleading_path='/tmp/spaced.docx',
    appendix_files=['nispach_1.pdf', 'nispach_2.pdf'],
    appendix_list=[
        {'id': '1', 'name': 'תיאור נספח 1'},
        {'id': '2', 'name': 'תיאור נספח 2'},
    ],
    output_path='out.pdf',
    style='arabic',
)
```

## Numbering Styles
* Hebrew letters: נספח א', נספח ב', ... up to ל' (30 max).
* Arabic numerals: נספח 1, 2, 3, ... unlimited.

## Reference Patterns
Family A (full נספח X), Family B (Gilad Cohen style), Family C (catch-all). Tolerates OCR space-removal (`\s*`), final-nun confusion, missing apostrophes. See `references/patterns-extracted.md`.

## Dependencies

System: `pandoc`, `tesseract-ocr`+`tesseract-ocr-heb`, `poppler-utils`, `libreoffice`, `ghostscript`, `fontconfig`.

Python: `weasyprint`, `pymupdf`, `pypdf`, `python-docx`, `pillow`, `python-bidi`.

```
pip install weasyprint pymupdf pypdf python-docx pillow python-bidi --break-system-packages
```

## Output Metadata

`bind_pleading()` returns `output_path`, `total_pages`, `expected_pages`, `file_size_mb`, `pleading_pages`, `toc_page`, `appendix_count`, `style`, `pages_match`, `page_map`, `preprocess_report`.

## Known Limitations
* Maximum 30 Hebrew appendices.
* Cover label max ~12 Hebrew characters at 48pt before line wrap.
* TOC overflow beyond ~25 entries (auto-detected at runtime).
* Tesseract not installed -> orientation skip warning.

## Edge Cases Handled
* OCR text without word spaces, final-nun confusion, missing apostrophes
* Mixed Hebrew/Arabic numbering
* DOCX with `.pdf` extension or vice versa (magic-byte detection)
* Phone photos rotated 90°/180°
* Long Hebrew appendix names (wrap inside cell)
* AI text with em dashes (sanitised before render)
* User has both DOCX and PDF in same folder (PDF preferred)
* Fresh Linux machine without Word fonts (auto-install from bundle)
