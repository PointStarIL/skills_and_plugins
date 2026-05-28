#!/usr/bin/env python3
"""
check_no_em_dash.py

סקריפט הבודק שלא נכנס מקף ארוך (U+2014) לקובץ DOCX או טקסט.
חוסם דחיית פלט שמכיל סימן זה.

שימוש:
    python3 check_no_em_dash.py /path/to/file.docx
    python3 check_no_em_dash.py /path/to/file.txt
"""

import sys
from pathlib import Path

EM_DASH = '—'
ALSO_PROBLEMATIC = ['ראוי לציין', 'כדאי להדגיש', 'חשוב להבין']


def check_docx(path):
    try:
        from docx import Document
    except ImportError:
        print('נדרש python-docx')
        return 1
    doc = Document(path)
    issues = []
    for i, p in enumerate(doc.paragraphs):
        if EM_DASH in p.text:
            issues.append(f'פסקה {i}: מקף ארוך נמצא')
        for phrase in ALSO_PROBLEMATIC:
            if phrase in p.text:
                issues.append(f'פסקה {i}: ביטוי AI חשוד "{phrase}"')
    return issues


def check_text_file(path):
    text = Path(path).read_text(encoding='utf-8')
    issues = []
    for line_num, line in enumerate(text.splitlines(), 1):
        if EM_DASH in line:
            issues.append(f'שורה {line_num}: מקף ארוך')
        for phrase in ALSO_PROBLEMATIC:
            if phrase in line:
                issues.append(f'שורה {line_num}: ביטוי AI חשוד "{phrase}"')
    return issues


def main():
    if len(sys.argv) < 2:
        print('שימוש: python3 check_no_em_dash.py /path/to/file')
        sys.exit(1)
    path = Path(sys.argv[1])
    if not path.exists():
        print(f'קובץ לא קיים: {path}')
        sys.exit(1)
    if path.suffix.lower() == '.docx':
        issues = check_docx(path)
    else:
        issues = check_text_file(path)
    if issues:
        print(f'נמצאו {len(issues)} בעיות:')
        for issue in issues:
            print(f'  - {issue}')
        sys.exit(2)
    print('עבר את הבדיקה: ללא מקפים ארוכים ובלי ביטויי AI אופייניים.')
    sys.exit(0)


if __name__ == '__main__':
    main()
