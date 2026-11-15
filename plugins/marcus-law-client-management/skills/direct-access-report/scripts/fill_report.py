# -*- coding: utf-8 -*-
"""ממלא את תבנית "דוח גישה ישירה" מתוך קובץ JSON ומפיק DOCX מוכן לשליחה.

שימוש:
    python3 fill_report.py <data.json> <output.docx> [template.docx]

כללים:
  * שדה שאינו מופיע ב-JSON  ->  נמחק מהמסמך (נשאר ריק).
  * שדה שמתחיל ב-chk_       ->  true = ☒ , false/חסר = ☐
  * ערך רב-שורתי (\\n)       ->  כל שורה הופכת לפסקה נפרדת ולא לשבירת שורה,
                                כדי שבפסקאות מיושרות לשני הצדדים השורה לא תימתח לרוחב העמוד.

עיצוב: הטקסט שממולא נכתב בריצה נפרדת משלו, שיורשת את הגופן והגודל של התווית
שלפניה אבל בלי קו תחתון. כך "פירוט:" נשאר עם קו תחתון והתשובה יוצאת נקייה.
"""
import copy
import json
import re
import sys

from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

CHECKED, UNCHECKED = '☒', '☐'
PATTERN = re.compile(r'\$\{(\w+)\}')


def resolve(name, data):
    if name.startswith('chk_'):
        return CHECKED if data.get(name) else UNCHECKED
    val = data.get(name, '')
    if val is None:
        val = ''
    if isinstance(val, (list, tuple)):
        val = '\n'.join(str(v) for v in val)
    return str(val)


def run_text(r):
    return ''.join(t.text or '' for t in r.findall(qn('w:t')))


def make_run(base_rPr, text, is_value):
    """בונה ריצה חדשה. בערך ממולא מסירים קו תחתון, כדי שלא יגלוש מהתווית."""
    r = OxmlElement('w:r')
    if base_rPr is not None:
        rPr = copy.deepcopy(base_rPr)
        if is_value:
            for u in rPr.findall(qn('w:u')):
                rPr.remove(u)
        r.append(rPr)
    t = OxmlElement('w:t')
    t.set(qn('xml:space'), 'preserve')
    t.text = text
    r.append(t)
    return r


def split_to_lines(text, data):
    """מפרק את הפסקה לשורות, וכל שורה לקטעים של (טקסט, האם זה ערך ממולא)."""
    segments = []
    pos = 0
    used = set()
    for m in PATTERN.finditer(text):
        if m.start() > pos:
            segments.append((text[pos:m.start()], False))
        used.add(m.group(1))
        segments.append((resolve(m.group(1), data), True))
        pos = m.end()
    if pos < len(text):
        segments.append((text[pos:], False))

    lines = [[]]
    for chunk, is_value in segments:
        parts = chunk.split('\n')
        for i, part in enumerate(parts):
            if i:
                lines.append([])
            if part:
                lines[-1].append((part, is_value))
    return lines, used


def fill(template, data, output):
    doc = Document(template)
    used = set()

    for p_el in list(doc.element.body.iter(qn('w:p'))):
        runs = p_el.findall(qn('w:r'))
        text = ''.join(run_text(r) for r in runs)
        if '${' not in text:
            continue

        source = next((r for r in runs if run_text(r).strip()), runs[0])
        base_rPr = source.find(qn('w:rPr'))
        pPr = p_el.find(qn('w:pPr'))

        lines, names = split_to_lines(text, data)
        used |= names

        for r in runs:
            p_el.remove(r)
        for chunk, is_value in lines[0]:
            p_el.append(make_run(base_rPr, chunk, is_value))

        # כל שורה נוספת הופכת לפסקה אמיתית, ולא לשבירת שורה בתוך אותה פסקה
        prev = p_el
        for line in lines[1:]:
            new_p = OxmlElement('w:p')
            if pPr is not None:
                new_p.append(copy.deepcopy(pPr))
            for chunk, is_value in line:
                new_p.append(make_run(base_rPr, chunk, is_value))
            prev.addnext(new_p)
            prev = new_p

    doc.save(output)

    unknown = sorted(set(data) - used)
    empty = sorted(n for n in used if not n.startswith('chk_') and not data.get(n))
    if unknown:
        print('אזהרה - מפתחות ב-JSON שאינם קיימים בתבנית:', ', '.join(unknown))
    if empty:
        print('שדות שנותרו ריקים:', ', '.join(empty))

    # קבוצות תיבות סימון שבדרך כלל אמורה להיות בהן בחירה אחת לפחות.
    # פרק ההמלצה (chk_rec_) אינו נבדק, כי כשקיים סיכוי משפטי הוא נשאר ריק בכוונה.
    groups = {
        'דחיפות ההליך': ['chk_urgency_regular', 'chk_urgency_urgent', 'chk_urgency_emergency'],
        'מהות הסיוע': ['chk_aid_appeal', 'chk_aid_consulting', 'chk_aid_additional_ni',
                       'chk_aid_additional_other', 'chk_aid_none'],
        'תקינות הקשר': ['chk_contact_ok', 'chk_contact_bad'],
        'מיצוי זכויות': ['chk_no_additional', 'chk_additional_ni', 'chk_additional_other'],
    }
    unchecked = [label for label, keys in groups.items()
                 if keys and not any(data.get(k) for k in keys)]
    if unchecked:
        print('קבוצות תיבות סימון שנותרו כולן ריקות:', ', '.join(unchecked))

    print('נוצר:', output)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    data_path, out_path = sys.argv[1], sys.argv[2]
    tpl = sys.argv[3] if len(sys.argv) > 3 else 'תבנית_דוח_גישה_ישירה.docx'
    with open(data_path, encoding='utf-8') as f:
        fill(tpl, json.load(f), out_path)
