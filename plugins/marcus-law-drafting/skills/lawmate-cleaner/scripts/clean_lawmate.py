#!/usr/bin/env python3
"""
Lawmate Cleaner - עיבוד טיוטות משפטיות שהופקו ממערכת law-mate.
"""

import argparse
import os
import re
import sys
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


BOLD_OPEN = '\x01'
BOLD_CLOSE = '\x02'


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


def clean_text(t: str) -> str:
    if not t:
        return t

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
    case_prefixes = ['עב"ל', 'ע"א', 'בג"ץ', 'ב"ל', 'ע"ע', 'תיק', 'בר"ע']
    for prefix in case_prefixes:
        t = re.sub(
            r'\[(' + re.escape(prefix) + r'[^\]]*?)\(LawMate\s+([^)]+)\)\]',
            _format_lawmate_citation, t)
        t = re.sub(
            r'\[(' + re.escape(prefix) + r'[^\]]*?)\(([\d./]+)\s+LawMate\)\]',
            _format_lawmate_citation, t)

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


MAIN_HEADING_EMU = 177800
SUB_HEADING_EMU = 152400


def classify_paragraph(p):
    raw = p.text.strip()
    if not raw:
        return None

    align = p.alignment
    bold = underline = False
    size = None
    if p.runs:
        r = p.runs[0]
        bold = bool(r.font.bold)
        underline = bool(r.font.underline)
        size = r.font.size
    style_name = p.style.name if p.style else ""

    is_centered = align == WD_ALIGN_PARAGRAPH.CENTER
    is_main = is_centered and bold and (
        size is None and style_name.startswith("Heading")
        or (size is not None and size >= MAIN_HEADING_EMU)
    )
    if is_main:
        return ("main_heading", clean_text(raw))

    if is_centered and underline:
        return ("sub_heading", clean_text(raw))

    if style_name == "Heading 2":
        return ("main_heading", clean_text(raw))

    if re.match(r'^\*\s+', raw):
        return ("bullet", clean_text(re.sub(r'^\*\s+', '', raw)))

    m = re.match(r'^(\d+|[א-ת])\.\s+(.*)$', raw)
    if m:
        return ("numbered", clean_text(m.group(2)))

    return ("body", clean_text(raw))


def extract_items(doc):
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
            if kind == "main_heading":
                in_body = True
            else:
                continue
        items.append((kind, text))
    return items


REMEDIES_KEYWORDS = ("סעד מבוקש", "סעדים מבוקשים", "הסעדים המבוקשים",
                    "סיכום וסעד", "סיכום והסעדים")
FINAL_KEYWORDS = ("סוף דבר", "אחרית דבר")


def _looks_like_remedies(text):
    return any(kw in text for kw in REMEDIES_KEYWORDS)


def _looks_like_final(text):
    return any(kw in text for kw in FINAL_KEYWORDS)


def post_process(items):
    fixed = []
    for kind, text in items:
        if kind == "sub_heading" and text.strip() == "הסעדים המבוקשים":
            kind = "main_heading"
        if kind == "main_heading":
            # Strip trailing clause; no em-dash reintroduction
            text = re.sub(r'\s*[—–\-]\s*עילת התביעה והסעדים המבוקשים\s*$', '', text)
            text = re.sub(r'\s*והסעדים המבוקשים\s*$', '', text)
        fixed.append((kind, text))

    has_main = any(k == "main_heading" for k, _ in fixed)
    has_sub = any(k == "sub_heading" for k, _ in fixed)
    if has_main and not has_sub:
        result = []
        synthetic_main_added = False
        for kind, text in fixed:
            if kind != "main_heading":
                result.append((kind, text))
                continue
            if _looks_like_remedies(text):
                result.append(("main_heading", "הסעדים המבוקשים"))
                synthetic_main_added = True
                continue
            if _looks_like_final(text):
                result.append(("main_heading", "סוף דבר"))
                synthetic_main_added = True
                continue
            if not synthetic_main_added:
                result.append(("main_heading", "פירוט הטענות"))
                synthetic_main_added = True
            result.append(("sub_heading", text))
        return result

    return fixed


FONT_NAME = "David"


def _set_rtl_paragraph(p):
    pPr = p._p.get_or_add_pPr()
    bidi = OxmlElement('w:bidi')
    bidi.set(qn('w:val'), '1')
    pPr.append(bidi)


def _set_rtl_run(r, bold=False, underline=False, size_pt=12):
    """Mark a run as RTL and set complex-script font + sizing.

    For Hebrew text in Word, complex-script properties (bCs, sz/szCs,
    rFonts/cs) are what actually drive bold/size rendering. Without bCs,
    Hebrew text never shows bold even though <w:b/> is set.
    """
    rPr = r._r.get_or_add_rPr()
    rtl = OxmlElement('w:rtl')
    rtl.set(qn('w:val'), '1')
    rPr.append(rtl)
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts')
        rPr.insert(0, rFonts)
    rFonts.set(qn('w:cs'), FONT_NAME)
    rFonts.set(qn('w:ascii'), FONT_NAME)
    rFonts.set(qn('w:hAnsi'), FONT_NAME)
    # Complex-script bold for Hebrew
    if bold:
        bCs = OxmlElement('w:bCs')
        bCs.set(qn('w:val'), '1')
        rPr.append(bCs)
    # Complex-script size
    szCs = OxmlElement('w:szCs')
    szCs.set(qn('w:val'), str(int(size_pt * 2)))
    rPr.append(szCs)


def _set_line_spacing(p, line_pts=18):
    pPr = p._p.get_or_add_pPr()
    spacing = pPr.find(qn('w:spacing'))
    if spacing is None:
        spacing = OxmlElement('w:spacing')
        pPr.append(spacing)
    spacing.set(qn('w:line'), '360')
    spacing.set(qn('w:lineRule'), 'auto')
    spacing.set(qn('w:after'), '120')


def _set_numbering(p, num_id, ilvl=0):
    pPr = p._p.get_or_add_pPr()
    numPr = OxmlElement('w:numPr')
    ilvl_el = OxmlElement('w:ilvl')
    ilvl_el.set(qn('w:val'), str(ilvl))
    numPr.append(ilvl_el)
    numId_el = OxmlElement('w:numId')
    numId_el.set(qn('w:val'), str(num_id))
    numPr.append(numId_el)
    pPr.append(numPr)


def _add_run(p, text, bold=False, underline=False, size_pt=12):
    r = p.add_run(text)
    r.font.name = FONT_NAME
    r.font.size = Pt(size_pt)
    r.font.bold = bold
    r.font.underline = underline
    _set_rtl_run(r, bold=bold, underline=underline, size_pt=size_pt)
    return r


def _add_formatted_text(p, text, bold=False, underline=False, size_pt=12):
    if not text:
        return
    if BOLD_OPEN not in text:
        _add_run(p, text, bold=bold, underline=underline, size_pt=size_pt)
        return
    pattern = re.compile(re.escape(BOLD_OPEN) + r'(.*?)' + re.escape(BOLD_CLOSE))
    pos = 0
    for m in pattern.finditer(text):
        if m.start() > pos:
            _add_run(p, text[pos:m.start()],
                     bold=bold, underline=underline, size_pt=size_pt)
        _add_run(p, m.group(1),
                 bold=True, underline=underline, size_pt=size_pt)
        pos = m.end()
    if pos < len(text):
        _add_run(p, text[pos:],
                 bold=bold, underline=underline, size_pt=size_pt)


def _setup_numbering_definitions(doc):
    numbering_xml = doc.part.numbering_part.element

    def make_abstract(abs_id, fmt):
        abs_el = OxmlElement('w:abstractNum')
        abs_el.set(qn('w:abstractNumId'), str(abs_id))
        lvl = OxmlElement('w:lvl')
        lvl.set(qn('w:ilvl'), '0')
        start = OxmlElement('w:start'); start.set(qn('w:val'), '1'); lvl.append(start)
        nfmt = OxmlElement('w:numFmt'); nfmt.set(qn('w:val'), fmt); lvl.append(nfmt)
        ltext = OxmlElement('w:lvlText'); ltext.set(qn('w:val'), '%1.'); lvl.append(ltext)
        ljc = OxmlElement('w:lvlJc'); ljc.set(qn('w:val'), 'start'); lvl.append(ljc)
        ppr = OxmlElement('w:pPr')
        ind = OxmlElement('w:ind')
        ind.set(qn('w:left'), '360'); ind.set(qn('w:hanging'), '360')
        ppr.append(ind); lvl.append(ppr)
        abs_el.append(lvl)
        return abs_el

    def make_num(num_id, abs_id):
        n = OxmlElement('w:num')
        n.set(qn('w:numId'), str(num_id))
        ref = OxmlElement('w:abstractNumId')
        ref.set(qn('w:val'), str(abs_id))
        n.append(ref)
        return n

    numbering_xml.append(make_abstract(20, 'decimal'))
    numbering_xml.append(make_abstract(21, 'hebrew1'))
    numbering_xml.append(make_num(10, 20))
    numbering_xml.append(make_num(11, 21))


def build_docx(items, output_path):
    doc = Document()

    section = doc.sections[0]
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(2.54)
    section.right_margin = Cm(2.54)
    sectPr = section._sectPr
    bidi = OxmlElement('w:bidi')
    sectPr.append(bidi)

    style = doc.styles['Normal']
    style.font.name = FONT_NAME
    style.font.size = Pt(12)
    rPr = style.element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts'); rPr.insert(0, rFonts)
    for attr in ('w:cs', 'w:ascii', 'w:hAnsi'):
        rFonts.set(qn(attr), FONT_NAME)

    _setup_numbering_definitions(doc)

    in_remedies = False
    remedies_intro_seen = False

    for kind, text in items:
        if kind == "main_heading":
            heading_text = text.replace(BOLD_OPEN, '').replace(BOLD_CLOSE, '')
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _set_rtl_paragraph(p)
            _set_line_spacing(p)
            _add_run(p, heading_text, bold=True, size_pt=14)
            in_remedies = (heading_text.strip() == "הסעדים המבוקשים")
            remedies_intro_seen = False
            continue

        if kind == "sub_heading":
            heading_text = text.replace(BOLD_OPEN, '').replace(BOLD_CLOSE, '')
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _set_rtl_paragraph(p)
            _set_line_spacing(p)
            _add_run(p, heading_text, underline=True, size_pt=12)
            continue

        if kind == "bullet":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            _set_rtl_paragraph(p)
            _set_line_spacing(p)
            _add_run(p, "• ", size_pt=12)
            _add_formatted_text(p, text, size_pt=12)
            continue

        if kind == "numbered":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            _set_rtl_paragraph(p)
            _set_line_spacing(p)
            if in_remedies and remedies_intro_seen:
                _set_numbering(p, num_id=11)
            else:
                _set_numbering(p, num_id=10)
                if in_remedies and not remedies_intro_seen:
                    remedies_intro_seen = True
            _add_formatted_text(p, text, size_pt=12)
            continue

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        _set_rtl_paragraph(p)
        _set_line_spacing(p)
        _add_formatted_text(p, text, size_pt=12)

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
        base, ext = os.path.splitext(args.input)
        output = f"{base}_מסודר.docx"

    print(f"Reading: {args.input}")
    src = Document(args.input)
    raw_para_count = len(src.paragraphs)

    items = extract_items(src)
    items = post_process(items)

    main_count = sum(1 for k, _ in items if k == "main_heading")
    sub_count = sum(1 for k, _ in items if k == "sub_heading")
    body_count = sum(1 for k, _ in items if k in ("body", "numbered"))
    bullet_count = sum(1 for k, _ in items if k == "bullet")

    full_raw_text = "\n".join(p.text for p in src.paragraphs)
    full_clean_text = "\n".join(t for _, t in items)
    raw_brackets = len(re.findall(r'\[[^\]]+\]', full_raw_text))
    clean_brackets = len(re.findall(r'\[[^\]]+\]', full_clean_text))
    lawmate_raw = len(re.findall(r'(?i)lawmate', full_raw_text))
    lawmate_clean = len(re.findall(r'(?i)lawmate', full_clean_text))
    raw_emdash = full_raw_text.count('—') + full_raw_text.count('–')
    clean_emdash = full_clean_text.count('—') + full_clean_text.count('–')
    raw_appendix = len(re.findall(r'\(\d{1,4}\)(?=\s*[.,;:]|\s*$)',
                                  full_raw_text, re.MULTILINE))
    clean_appendix = len(re.findall(r'\(\d{1,4}\)(?=\s*[.,;:]|\s*$)',
                                    full_clean_text, re.MULTILINE))
    bold_count = full_clean_text.count(BOLD_OPEN)

    build_docx(items, output)

    print(f"\n  Wrote: {output}")
    print(f"  Paragraphs in source: {raw_para_count}")
    print(f"  Items in output: {len(items)}")
    print(f"  Main headings: {main_count}")
    print(f"  Sub-headings: {sub_count}")
    print(f"  Body items: {body_count}")
    print(f"  Bullets: {bullet_count}")
    print(f"  Bracket refs: {raw_brackets} -> {clean_brackets}")
    print(f"  LawMate mentions: {lawmate_raw} -> {lawmate_clean}")
    print(f"  Em/en dashes: {raw_emdash} -> {clean_emdash}")
    print(f"  Appendix refs (N): {raw_appendix} -> {clean_appendix}")
    print(f"  Bolded party citations: {bold_count}")


if __name__ == "__main__":
    main()
