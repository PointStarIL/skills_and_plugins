---
name: build-appendix-pdf
description: "מארגן, ממספר וכורך נספחים של כתבי בי-דין ל-PDF מוכן להגשה לבית המשפט: מספור עברי/ערבי, אימות הפניות צולבות מול גוף כתב הטענות, דפי כיסוי, תוכן עניינים וסימניות. ממיר DOCX ל-PDF תוך שמירת עיצוב Word (פונטים מצורפים), אוכף מרווח 1.5 בגוף ו-1.15 בטבלאות, מנקה מקף ארוך, ומתקן כיוון עמוד. הפעל כאשר: 'כרוך נספחים', 'נספחים', 'דפי כיסוי', 'אימות הפניות', 'bind appendices', 'appendix package'."
metadata:
  version: "1.1.0"
---

# build-appendix-pdf

## Soul
I organize, number, and bind legal pleading appendices into court-ready PDFs. I manage Hebrew and Arabic numbering styles, validate cross-references against the pleading text, and produce professional court documents with complete metadata tracking. I enforce **five Iron Rules** that guarantee the output is correctly oriented, properly rendered, formatted to match a human-typed Word document, free of AI-giveaway typography, and rendered with the right Word fonts on any machine.

## מנוע ה-DOCX היחיד

הסקיל הזה **ממיר** DOCX ל-PDF ואינו בונה מסמכי Word. כל DOCX שנבנה במערכת נבנה דרך
המנוע היחיד, `hebrew-docx-engine` שבאותה חבילה
(`skills/hebrew-docx-engine/scripts/docx_hebrew_engine.py` + `references/template.docx`).
אם נדרש לייצר כאן מסמך Word חדש, יש לבנות אותו דרך המנוע ולא ידנית. `prepare_docx.py`
משנה מרווחי שורות לצורך ההמרה ל-PDF בלבד, ואינו מגדיר סגנונות.

## Iron Rules

### Iron Rule 1 - DOCX must be converted to PDF
LibreOffice headless (with installed Word fonts) is primary. WeasyPrint is fallback. Detection via magic bytes, not extension.

### Iron Rule 2 - Orientation must be detected and fixed
Tesseract OSD on every image-based page; auto-rotate 90°/180°/270°.

### Iron Rule 3 - No em dashes in Claude-generated chrome
Every TOC header, TOC row, cover-page name, bookmark label, and metadata string passes through `sanitize_text.sanitize()`. Em dashes (U+2014) and en dashes (U+2013) are replaced with hyphen-minus.

### Iron Rule 4 - Prefer sibling PDF over DOCX conversion
When `bind_pleading('X.docx', ..., prefer_sibling_pdf=True)` and `X.pdf` exists in the same directory, the PDF is used (preserves the user's manual Word export).

### Iron Rule 5 - Word fonts ensured on every run
Before every binding, `ensure_fonts_installed()` checks fontconfig for David / Times New Roman / Arial. If missing, copies bundled TTFs from `<skill>/fonts/` into `~/.fonts` and refreshes `fc-cache`. No-op when fonts are already installed. Skill is fully portable across machines.

## Folder Layout

```
build-appendix-pdf/
├── SKILL.md
├── INSTALL.md
├── CHANGELOG.md
├── fonts/
│   ├── README.md           licensing notice
│   ├── david.ttf, davidbd.ttf
│   ├── times.ttf, timesbd.ttf, timesi.ttf, timesbi.ttf
│   ├── arial.ttf, arialbd.ttf, ariali.ttf, arialbi.ttf, ariblk.ttf
│   └── ARIALN*.TTF, ARLRDBD.TTF
├── references/
│   ├── patterns-extracted.md
│   └── self-check.md         הצ'קליסט הבינארי לפני החזרת התיק
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
    └── validate_references.py  שער 1: אימות הפניות צולבות (CLI, exit 1 בכשל)
```

## Workflow

```python
from prepare_docx import prepare_pleading
from bind_pdf import bind_pleading

APPENDIX_LIST = [
    {'id': '1', 'name': 'תיאור נספח 1'},
    {'id': '2', 'name': 'תיאור נספח 2'},
]

# 1. Apply 1.5 body / 1.15 table line spacing + sanitise dashes in DOCX
prepare_pleading('pleading.docx', '/tmp/spaced.docx')

# 2. Bind. Auto-installs fonts on first run, sanitises appendix names,
#    prefers sibling PDF if it exists.
result = bind_pleading(
    pleading_path='/tmp/spaced.docx',
    appendix_files=['nispach_1.pdf', 'nispach_2.pdf'],
    appendix_list=APPENDIX_LIST,
    output_path='out.pdf',
    style='arabic',
)
```

### שער 1, אימות הפניות צולבות (לפני הכריכה)

**חובה. הרץ לפני `bind_pleading`,** אחרת ייכרך תיק שבו כתב הטענות מפנה לנספח שאינו קיים,
או שנספח נכרך ואיש אינו מפנה אליו. שתי התקלות מתגלות בבית המשפט ולא כאן.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/build-appendix-pdf/scripts/validate_references.py" /tmp/spaced.docx --appendix-list applist.json
```

`applist.json` הוא בדיוק אותו `APPENDIX_LIST`. קוד יציאה: `0` תקין, `1` נמצאו שגיאות,
`2` לא חולץ טקסט (PDF סרוק ללא שכבת טקסט: הרץ OCR תחילה, אל תתעלם).

- `orphaned_references` (הפניה לנספח שאינו ברשימה) → **עצור.** או שחסר נספח, או שההפניה שגויה.
- `missing_references` (נספח ברשימה שאיש אינו מפנה אליו) → **עצור ושאל את המשתמש.**
  לפעמים זה מכוון, אבל זו החלטה שלו ולא שלך.

**אל תכרוך על יציאה שאינה 0.**

### שער 2, `pages_match` (אחרי הכריכה)

`bind_pleading()` מחזיר `pages_match`, `expected_pages` ו-`total_pages`. הוא סופר בעצמו
אם התיק הכרוך מכיל את מספר העמודים שהיה אמור להכיל.

```python
if not result['pages_match']:
    raise SystemExit(
        f"כשל כריכה: צפוי {result['expected_pages']} עמודים, "
        f"בפועל {result['total_pages']}."
    )
```

**`pages_match == False` פירושו שעמודים אבדו או שוכפלו בכריכה. אל תחזיר את ה-PDF למשתמש.**
דווח על הפער, ציין את שני המספרים, ובדוק מול `page_map` איזה נספח לא נכרך כראוי.

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

`pages_match` אינו מידע לעיון: הוא **שער 2** שבסעיף Workflow. חובה לבדוק אותו לפני החזרת הפלט.

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

## בדיקה עצמית סופית (חובה)

**אל תחזיר את התיק הכרוך לפני שהשלמת את הצעדים האלה והצגת את הטבלה.**

1. הרץ את **שער 1** (`validate_references.py`) ואת **שער 2** (`pages_match`) שבסעיף
   Workflow. קוד יציאה שאינו `0`, או `pages_match == False`, עוצרים את התהליך.
2. קרא את `references/self-check.md` ודרג את עצמך מול כל שש השורות.
3. **הצג את הטבלה למשתמש, לפני הקובץ.** לכל שורה `✓` או `✗` ו**ראיה מצוטטת**.
   שורה בלי ראיה נחשבת `✗`. בדיקה שלא רצה נכתבת **"לא נבדק"**, לעולם לא `✓`.
4. כל `✗` → תקן וחזור לצעד 1.
5. כן או לא בלבד. אין "בערך" ואין "נראה תקין".

```
בדיקה עצמית - תיק נספחים - עת 12345-06-26.pdf
──────────────────────────────────────────────────────────
1. הפניות צולבות תקינות?     ✓  exit 0, 14 הפניות, 0 יתומות
2. pages_match?               ✓  צפוי 87, בפועל 87
3. דף שער לכל נספח?           ✓  appendix_count=9, ברשימה 9
4. TOC תואם ל-page_map?       ✗  נספח 6: ב-TOC עמ' 54, ב-page_map עמ' 56
5. כיוון עמודים נבדק?         ✓  preprocess_report: 3 עמודים סובבו, 0 אזהרות
6. פונטים הותקנו?             ✓  David/Times/Arial כבר קיימים
──────────────────────────────────────────────────────────
תוצאה: 5/6 עברו. מתקן את 4 ומריץ שוב.
```
