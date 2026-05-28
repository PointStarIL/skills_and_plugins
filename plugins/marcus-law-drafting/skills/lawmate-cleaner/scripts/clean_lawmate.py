#!/usr/bin/env python3
"""
Lawmate Cleaner - עיבוד טיוטות משפטיות שהופקו ממערכת law-mate.

הסקריפט מנקה את הטקסט (LawMate stamps, file refs, em-dashes, LRM/RLM marks,
date normalisation, citation deduplication) ובונה DOCX מעוצב על-בסיס תבנית
(`references/template.docx`) שכוללת סגנונות בשם: Normal, List Paragraph
(decimal auto-numbering), Heading 2, hebrew1 numbering לסעדים.

מבנה הפלט:
- פסקת גוף: List Paragraph (מספור 1, 2, 3 רץ דרך style inheritance)
- אזכור נספח ("מצורף ומסומן כנספח N"): List Paragraph + numId=0 (override),
  עם קו תחתון
- סעד ("א.", "ב.", "ג." בתחילת פסקה): List Paragraph + hebrew1 numbering,
  הקידומת מוסרת
- כותרת-משנה (centered + bold בקלט): Heading 2
"""

import argparse
import os
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


BOLD_OPEN = '\x01'
BOLD_CLOSE = '\x02'

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "references" / "template.docx"

# numId values defined in template.docx's numbering.xml:
EXHIBIT_NUMID = 0      # override → "no list" (paragraph gets underline only)
REMEDY_NUMID = 43      # → abstractNumId=7 (hebrew1: א., ב., ג., ד.)

# Style names (resolved by python-docx via name → styleId lookup)
STYLE_BODY = "List Paragraph"
STYLE_HEADING = "Heading 2"

# EMU thresholds for heading detection in lawmate input
MAIN_HEADING_EMU = 177800   # 14pt
SUB_HEADING_EMU = 152400    # 12pt

# Detection patterns
EXHIBIT_RE = re.compile(r'מצורף\s+ומסומן\s+כנספח\s+\d+')
REMEDY_PREFIX_RE = re.compile(r'^([א-ת])\.\s+(.+)$', re.DOTALL)


def _bold_parties(parties: str) -> str:
    parties = parties.strip().strip(',').strip()
    if not re.search(r'[א-ת]', parties):
        return parties
    return f'{BOLD_OPEN}{parties}{BOLD_CLOSE}'


def _format_full_citation(m):
    court = m.group(1).strip()
    case_id = m.group(2).strip()
    parties = m.group(3).strip()
    date = m.group(4).strip()
    if not re.search(r'[א-ת]', parties.replace('נ', '')):
        return ''
    return f'({court}, {case_id}, {_bold_parties(parties)}, {date})'


def _format_lawmate_citation(m):
    inner = m.group(1).strip()
    date = m.group(2).strip()
    parts = inner.split(None, 2)
    if len(parts) == 3:
        prefix, case_id, parties = parts
        if re.search(r'[א-ת]', parties.replace('נ', '')):
            return f'{prefix} {case_id} {_bold_parties(parties)} ({date})'
    return f'{inner} ({date})'


def _format_paren_lawmate_citation(m):
    """Format: (PREFIX CASE_ID PARTIES (DATE LawMate)) -> (PREFIX CASE_ID **PARTIES** (DATE))"""
    prefix = m.group(1).strip()
    case_id = m.group(2).strip()
    parties = m.group(3).strip().rstrip(',').strip()
    date = m.group(4).strip()
    if not re.search(r'[א-ת]', parties.replace('נ', '')):
        return ''
    return f'({prefix} {case_id} {_bold_parties(parties)} ({date}))'


def clean_text(t: str) -> str:
    if not t:
        return t

    # -1. Strip directional marks (LRM/RLM) that fragment regex matching
    t = t.replace('‎', '').replace('‏', '')

    # 0. Normalise dates DD/MM/YYYY -> DD.MM.YYYY. Case numbers (e.g.
    #    64925-09-25) and law years (e.g. התשנ"ה-1995) use hyphens, so they
    #    are never touched by this slash-only pattern.
    t = re.sub(r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b', r'\1.\2.\3', t)

    # 1. Remove trailing appendix/page references ] (12) -> ]
    t = re.sub(r'\]\s*\(\d{1,4}\)', ']', t)

    # 2. Replace em/en dashes with hyphens (AI tell)
    t = t.replace('—', '-').replace('–', '-')

    # 3. Full-format citations: [court, case_id, parties, date]
    t = re.sub(
        r'\[([^,\]]+),\s*([^,\]]+),\s*([^\]]*?נ[\'.]\s*[^,\]]*?),\s*([\d./]+)\]',
        _format_full_citation, t,
    )

    # 4. Case-law citations with LawMate stamp
    case_prefixes = ['עב"ל', 'ע"א', 'בג"ץ', 'בג"צ', 'ב"ל', 'ע"ע', 'תיק', 'בר"ע']
    for prefix in case_prefixes:
        # 4a. Bracket format: [PREFIX ... (LawMate DATE)]
        t = re.sub(
            r'\[(' + re.escape(prefix) + r'[^\]]*?)\(LawMate\s+([^)]+)\)\]',
            _format_lawmate_citation, t)
        # 4b. Bracket format: [PREFIX ... (DATE LawMate)]
        t = re.sub(
            r'\[(' + re.escape(prefix) + r'[^\]]*?)\(([\d./]+)\s+LawMate\)\]',
            _format_lawmate_citation, t)
        # 4c. Paren format: (PREFIX CASE_ID PARTIES (DATE LawMate))
        t = re.sub(
            r'\(\s*(' + re.escape(prefix) + r')\s+([^\s()]+)\s+([^()]+?)\s*\(\s*([\d./]+)\s+LawMate\s*\)\s*\)',
            _format_paren_lawmate_citation, t)
        # 4d. Paren format: (PREFIX CASE_ID PARTIES (LawMate DATE))
        t = re.sub(
            r'\(\s*(' + re.escape(prefix) + r')\s+([^\s()]+)\s+([^()]+?)\s*\(\s*LawMate\s+([\d./]+)\s*\)\s*\)',
            _format_paren_lawmate_citation, t)

    # 5. File references
    t = re.sub(r'\s*\[תיק-\d+[^\]]*\]', '', t)
    t = re.sub(r'\s*\[[^\]]*\.(pdf|docx)[^\]]*\]', '', t)
    t = re.sub(r"\s*\[[^\]]*?עמ'[^\]]*\]", '', t)

    # 6. General law-citation brackets
    t = re.sub(r'\s*\[חוק[^\]]+\]', '', t)

    # 7. Bare (N) appendix references at end of sentence
    t = re.sub(r'\s+\(\d{1,4}\)(?=\s*[.,;:]|\s*$)', '', t)

    # 8. Whitespace cleanup (don't touch \x01/\x02)
    t = re.sub(r'[ \t]+', ' ', t)
    t = re.sub(r'\s+([.,;:])', r'\1', t)
    t = re.sub(r'\(\s+', '(', t)
    t = re.sub(r'\s+\)', ')', t)
    return t.strip()


def classify_paragraph(p):
    """Classify a paragraph into one of: sub_heading, exhibit_ref, remedy, body.

    Returns (kind, cleaned_text) or None for empty paragraphs.
    """
    raw = p.text.strip()
    if not raw:
        return None

    align = p.alignment
    bold = False
    size = None
    if p.runs:
        r = p.runs[0]
        bold = bool(r.font.bold)
        size = r.font.size
    style_name = p.style.name if p.style else ""

    is_centered = align == WD_ALIGN_PARAGRAPH.CENTER
    is_heading = (
        (is_centered and bold and (size is None or size >= SUB_HEADING_EMU))
        or style_name in ("Heading 1", "Heading 2")
    )
    if is_heading:
        return ("sub_heading", clean_text(raw))

    cleaned = clean_text(raw)
    if not cleaned:
        return None

    if EXHIBIT_RE.search(cleaned):
        return ("exhibit_ref", cleaned)

    m = REMEDY_PREFIX_RE.match(cleaned)
    if m:
        return ("remedy", m.group(2).strip())

    return ("body", cleaned)


def extract_items(doc):
    """Walk the lawmate doc, skip the title-block envelope, classify each
    substantive paragraph. The body begins at the first heading."""
    items = []
    in_body = False
    for p in doc.paragraphs:
        c = classify_paragraph(p)
        if c is None:
            continue
        kind, text = c
        if not text:
            continue
        if not in_body:
            if kind == "sub_heading":
                in_body = True
            else:
                continue
        items.append((kind, text))
    return items


_CITE_PREFIXES = '(?:עב"ל|ע"א|בג"ץ|בג"צ|ב"ל|ע"ע|תיק|בר"ע)'
_CITE_RE = re.compile(
    r'\(\s*(' + _CITE_PREFIXES + r')\s+'
    r'([\S]+?)\s+'
    + re.escape(BOLD_OPEN) + r'([^' + re.escape(BOLD_CLOSE) + r']+)' + re.escape(BOLD_CLOSE)
    + r'\s*(?:\(\s*([\d./]+)\s*\)|,\s*([\d./]+))\s*\)'
)


def _last_party_name(parties: str) -> str:
    m = re.split(r"\s+נ['.]\s+", parties, maxsplit=1)
    first_party = m[0].strip()
    tokens = first_party.split()
    if not tokens:
        return parties
    return tokens[-1]


def dedup_citations(items):
    """Replace repeat full citations of the same case_id with 'עניין LASTNAME'."""
    seen = {}

    def replace(m):
        case_id = m.group(2)
        parties = m.group(3)
        if case_id in seen:
            last = seen[case_id]
            return f'עניין {BOLD_OPEN}{last}{BOLD_CLOSE}'
        last = _last_party_name(parties)
        seen[case_id] = last
        return m.group(0)

    out = []
    for kind, text in items:
        if kind in ('body', 'exhibit_ref', 'remedy'):
            text = _CITE_RE.sub(replace, text)
        out.append((kind, text))
    return out


# ----- DOCX building (template-based) -----------------------------------


def _set_numbering(p, num_id, ilvl=0):
    """Apply explicit numPr (overrides the style's inherited numbering)."""
    pPr = p._p.get_or_add_pPr()
    numPr = OxmlElement('w:numPr')
    ilvl_el = OxmlElement('w:ilvl')
    ilvl_el.set(qn('w:val'), str(ilvl))
    numPr.append(ilvl_el)
    numId_el = OxmlElement('w:numId')
    numId_el.set(qn('w:val'), str(num_id))
    numPr.append(numId_el)
    pPr.append(numPr)


def _apply_paragraph_underline(p):
    """Add paragraph-level rPr with single underline. Affects auto-rendered list
    marker (if any) and any subsequent runs that don't override."""
    pPr = p._p.get_or_add_pPr()
    rPr = pPr.find(qn('w:rPr'))
    if rPr is None:
        rPr = OxmlElement('w:rPr')
        pPr.append(rPr)
    u = OxmlElement('w:u')
    u.set(qn('w:val'), 'single')
    rPr.append(u)


def _add_run(p, text, bold=False, underline=False):
    """Add a run. Styling (font, size, RTL) comes from the paragraph's style."""
    r = p.add_run(text)
    if bold:
        r.bold = True
        # Complex-script bold (Hebrew renders bold only with bCs)
        rPr = r._r.get_or_add_rPr()
        bCs = OxmlElement('w:bCs')
        rPr.append(bCs)
    if underline:
        r.underline = True
    return r


def _add_formatted_text(p, text, underline=False):
    """Add text with inline bold markers (\\x01..\\x02 around party names)
    converted to bold runs. underline=True applies to every run."""
    if not text:
        return
    if BOLD_OPEN not in text:
        _add_run(p, text, underline=underline)
        return
    pattern = re.compile(re.escape(BOLD_OPEN) + r'(.*?)' + re.escape(BOLD_CLOSE))
    pos = 0
    for m in pattern.finditer(text):
        if m.start() > pos:
            _add_run(p, text[pos:m.start()], underline=underline)
        _add_run(p, m.group(1), bold=True, underline=underline)
        pos = m.end()
    if pos < len(text):
        _add_run(p, text[pos:], underline=underline)


def build_docx(items, output_path):
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Template not found: {TEMPLATE_PATH}")
    doc = Document(str(TEMPLATE_PATH))

    # Remove the placeholder paragraph in the template
    placeholder = doc.paragraphs[0]
    placeholder._element.getparent().remove(placeholder._element)

    for kind, text in items:
        if kind == "sub_heading":
            clean = text.replace(BOLD_OPEN, '').replace(BOLD_CLOSE, '')
            p = doc.add_paragraph(style=STYLE_HEADING)
            _add_run(p, clean)
            continue

        if kind == "exhibit_ref":
            p = doc.add_paragraph(style=STYLE_BODY)
            _set_numbering(p, EXHIBIT_NUMID)   # override → no list marker
            _apply_paragraph_underline(p)
            _add_formatted_text(p, text, underline=True)
            continue

        if kind == "remedy":
            p = doc.add_paragraph(style=STYLE_BODY)
            _set_numbering(p, REMEDY_NUMID)    # hebrew1 (א., ב., ג., ד.)
            _add_formatted_text(p, text)
            continue

        # body
        p = doc.add_paragraph(style=STYLE_BODY)
        _add_formatted_text(p, text)

    doc.save(output_path)


def main():
    parser = argparse.ArgumentParser(description="Clean a law-mate DOCX draft.")
    parser.add_argument("input", help="Path to input DOCX from law-mate")
    parser.add_argument("output", nargs="?",
                        help="Path for cleaned DOCX")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    output = args.output
    if output is None:
        base, _ = os.path.splitext(args.input)
        output = f"{base}_מסודר.docx"

    print(f"Reading: {args.input}")
    src = Document(args.input)
    raw_para_count = len(src.paragraphs)

    items = extract_items(src)
    items = dedup_citations(items)

    sub_count = sum(1 for k, _ in items if k == "sub_heading")
    body_count = sum(1 for k, _ in items if k == "body")
    exhibit_count = sum(1 for k, _ in items if k == "exhibit_ref")
    remedy_count = sum(1 for k, _ in items if k == "remedy")

    full_raw_text = "\n".join(p.text for p in src.paragraphs)
    full_clean_text = "\n".join(t for _, t in items)
    raw_brackets = len(re.findall(r'\[[^\]]+\]', full_raw_text))
    clean_brackets = len(re.findall(r'\[[^\]]+\]', full_clean_text))
    lawmate_raw = len(re.findall(r'(?i)lawmate', full_raw_text))
    lawmate_clean = len(re.findall(r'(?i)lawmate', full_clean_text))
    raw_emdash = full_raw_text.count('—') + full_raw_text.count('–')
    clean_emdash = full_clean_text.count('—') + full_clean_text.count('–')
    bold_count = full_clean_text.count(BOLD_OPEN)

    build_docx(items, output)

    print(f"\n  Wrote: {output}")
    print(f"  Paragraphs in source: {raw_para_count}")
    print(f"  Items in output: {len(items)}")
    print(f"  Sub-headings (Heading 2): {sub_count}")
    print(f"  Body paragraphs (numbered 1,2,3): {body_count}")
    print(f"  Exhibit references (underlined): {exhibit_count}")
    print(f"  Remedies (א, ב, ג, ד): {remedy_count}")
    print(f"  Bracket refs: {raw_brackets} -> {clean_brackets}")
    print(f"  LawMate mentions: {lawmate_raw} -> {lawmate_clean}")
    print(f"  Em/en dashes: {raw_emdash} -> {clean_emdash}")
    print(f"  Bolded party citations: {bold_count}")


if __name__ == "__main__":
    main()
