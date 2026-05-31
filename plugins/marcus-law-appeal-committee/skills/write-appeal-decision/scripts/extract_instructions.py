#!/usr/bin/env python3
"""
extract_instructions.py

סקריפט לסריקת טיוטת DOCX וזיהוי כל ההוראות שסומנו בסוגריים זוויתיים <>.
מייצר טבלה מסודרת המוצגת למשתמש לפני הכתיבה.

שימוש:
    python3 extract_instructions.py /path/to/draft.docx

פלט:
    - טבלה Markdown לתצוגה.
    - קובץ JSON עם מבנה ההוראות (אם נדרש).
"""

import sys
import json
import re
from pathlib import Path

try:
    from docx import Document
except ImportError:
    print("נדרש python-docx. התקנה: pip install python-docx")
    sys.exit(1)


INSTRUCTION_PATTERN = re.compile(r'<([^>]+)>', re.UNICODE)


def classify_instruction(text):
    """סיווג ראשוני של סוג ההוראה לפי מילות מפתח."""
    text_lower = text.lower()
    if 'תנסח מחדש' in text or 'תערוך' in text or 'נסח מחדש' in text:
        if 'תרחיב' in text or 'הרחב' in text:
            return 'ניסוח מחדש + הרחבה'
        return 'ניסוח מחדש'
    if 'תרחיב' in text or 'הרחב' in text:
        return 'הרחבה'
    if 'תכניס לתוך' in text or 'הפנה' in text:
        return 'הפניה / הכנסה לסעיף אחר'
    if 'פה אני רוצה שנוסיף' in text or 'תוסיף' in text:
        return 'הוספת תוכן ספציפי'
    if 'תנסח' in text or 'תכתוב' in text or 'נסח' in text or 'כתוב' in text:
        return 'כתיבה חדשה מאפס'
    return 'אחר / כללי'


def shorten(text, max_chars=80):
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 1] + '…'


def extract(docx_path):
    doc = Document(docx_path)
    findings = []
    block_open = None
    block_lines = []
    for i, p in enumerate(doc.paragraphs):
        text = p.text
        opens = [m.start() for m in re.finditer(r'<', text)]
        closes = [m.start() for m in re.finditer(r'>', text)]

        if block_open is None:
            for m in INSTRUCTION_PATTERN.finditer(text):
                findings.append({
                    'paragraph_index': i,
                    'paragraph_text_preview': shorten(text, 100),
                    'instruction_text': m.group(1).strip(),
                    'type': classify_instruction(m.group(1)),
                    'span': 'single'
                })
            unclosed = len(opens) - len(closes)
            if unclosed > 0:
                last_open = text.rfind('<')
                content_after = text[last_open + 1:]
                if '>' not in content_after:
                    block_open = i
                    block_lines = [content_after]
        else:
            if '>' in text:
                close_idx = text.find('>')
                block_lines.append(text[:close_idx])
                findings.append({
                    'paragraph_index': f'{block_open}-{i}',
                    'paragraph_text_preview': shorten(' / '.join(block_lines)[:200], 200),
                    'instruction_text': ' '.join(block_lines).strip(),
                    'type': classify_instruction(' '.join(block_lines)),
                    'span': 'multi'
                })
                block_open = None
                block_lines = []
            else:
                block_lines.append(text)
    return findings


def print_markdown_table(findings):
    print('| # | פסקה | סוג | טקסט ההוראה (קטע) |')
    print('|---|------|-----|--------------------|')
    for n, f in enumerate(findings, 1):
        print(f"| {n} | {f['paragraph_index']} | {f['type']} | {shorten(f['instruction_text'], 80)} |")


def main():
    if len(sys.argv) < 2:
        print('שימוש: python3 extract_instructions.py /path/to/draft.docx')
        sys.exit(1)
    path = Path(sys.argv[1])
    if not path.exists():
        print(f'קובץ לא קיים: {path}')
        sys.exit(1)
    findings = extract(path)
    print(f'נמצאו {len(findings)} הוראות בטיוטה.\n')
    print_markdown_table(findings)
    out_json = path.with_suffix('.instructions.json')
    out_json.write_text(json.dumps(findings, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\nהפלט המובנה נשמר ל-: {out_json}')


if __name__ == '__main__':
    main()
