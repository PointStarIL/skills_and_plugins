# -*- coding: utf-8 -*-
"""בונה מכתב "סיכום הייעוץ שניתן" בעברית RTL מתוך קובץ JSON.

שימוש:
    python3 make_letter.py <letter.json> <output.docx>

מבנה ה-JSON:
{
  "letterDate":  "28.07.2026",
  "clientName":  "מר אברהם כהן",
  "subject":     "סיכום הייעוץ שניתן - תיק סיוע משפטי 2141362",
  "body":        ["פסקה ראשונה", "פסקה שנייה", "..."]
}

עיצוב: אם התוסף marcus-law-drafting מותקן, המכתב נבנה על מנוע hebrew-docx-engine
כדי שיצא זהה לשאר מסמכי המשרד. אם לא, יש נפילה לבנייה עצמאית ב-python-docx
עם David 12, RTL ומרווח 1.5.
"""
import json
import sys
from pathlib import Path

ENGINE_PATHS = [
    Path.home() / '.claude/plugins/synced/marcus-law-drafting/skills/hebrew-docx-engine/scripts',
    Path('/root/.claude/plugins/synced/marcus-law-drafting/skills/hebrew-docx-engine/scripts'),
]

hd = None
for p in ENGINE_PATHS:
    if (p / 'docx_hebrew_engine.py').exists():
        sys.path.insert(0, str(p))
        import docx_hebrew_engine as hd  # noqa: E402
        break


def build_with_engine(d, out):
    doc = hd.open_document()
    for line in [d['letterDate'], '', 'לכבוד', d['clientName'], '',
                 'העתק: הלשכה לסיוע משפטי', '']:
        hd.add_plain(doc, line)
    p = doc.add_paragraph()
    hd.set_numbering(p, 0)
    hd.add_run(p, 'הנדון: ' + d['subject'], bold=True, underline=True)
    hd.add_plain(doc, '')
    for para in d['body']:
        hd.add_body(doc, hd.sanitize_source_text(para))
    for line in ['', 'בכבוד רב,', '', 'חיים מרכוס, עו"ד',
                 'ע"פ מינוי מכוח חוק הסיוע המשפטי']:
        hd.add_plain(doc, line)
    hd.save(doc, out)


def build_fallback(d, out):
    from docx import Document
    from docx.shared import Pt, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    doc = Document()
    st = doc.styles['Normal']
    st.font.name = 'David'
    st.font.size = Pt(12)
    st.element.rPr.rFonts.set(qn('w:cs'), 'David')
    for s in doc.sections:
        s.top_margin = Cm(2.54)
        s.bottom_margin = Cm(1.9)
        s.left_margin = s.right_margin = Cm(3.17)

    def para(text, bold=False, underline=False, justify=False, numbered=False):
        p = doc.add_paragraph()
        pPr = p._p.get_or_add_pPr()
        bidi = OxmlElement('w:bidi')
        pPr.append(bidi)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY if justify else WD_ALIGN_PARAGRAPH.RIGHT
        p.paragraph_format.line_spacing = 1.5
        r = p.add_run(text)
        r.bold = bold
        r.underline = underline
        rPr = r._r.get_or_add_rPr()
        rPr.append(OxmlElement('w:rtl'))
        if bold:
            rPr.append(OxmlElement('w:bCs'))
        return p

    for line in [d['letterDate'], '', 'לכבוד', d['clientName'], '',
                 'העתק: הלשכה לסיוע משפטי', '']:
        para(line)
    para('הנדון: ' + d['subject'], bold=True, underline=True)
    para('')
    for i, text in enumerate(d['body'], 1):
        para('%d. %s' % (i, text), justify=True)
    for line in ['', 'בכבוד רב,', '', 'חיים מרכוס, עו"ד',
                 'ע"פ מינוי מכוח חוק הסיוע המשפטי']:
        para(line)
    doc.save(out)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    with open(sys.argv[1], encoding='utf-8') as f:
        data = json.load(f)
    out = sys.argv[2]
    if hd is not None:
        build_with_engine(data, out)
        print('נוצר על מנוע hebrew-docx-engine:', out)
    else:
        build_fallback(data, out)
        print('נוצר בבנייה עצמאית (מנוע hebrew-docx-engine לא נמצא):', out)


if __name__ == '__main__':
    main()
