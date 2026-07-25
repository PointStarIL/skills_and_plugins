#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ייצוא טקסט טהור (Markdown) מפלט OCR, לצד קובצי ה-PDF של התיק.

שכבת הטקסט שמוטמעת ב-PDF (ראה embed_text_layer.py) מספיקה לחיפוש, אבל
איכותה נמוכה מזו של Mistral OCR ולא נוח לצטט ממנה. הסקריפט הזה שומר את
פלט ה-OCR האיכותי כקובצי .md נקראים, עם סימון עמודים, בתיקייה
"ניתוח מסמכים/טקסט OCR" שמשקפת את מבנה התיק.

התוצאה: לכל PDF בתיק יש קובץ .md מקביל שאפשר לחפש בו, לצטט ממנו
ולהאכיל אותו לסקילים אחרים בלי להריץ OCR מחדש.

שימוש כספרייה (הדרך המומלצת, כשהטקסט כבר בידך):

    from export_ocr_text import write_markdown, slice_pages, parse_pages

    pages = parse_pages(open("erar_full.txt").read())   # dict: מספר עמוד -> טקסט
    write_markdown(pages, "out/כתב ערר - 19.02.25.md", "כתב ערר - 19.02.25")

    # לנספח שפוצל מתוך קובץ גדול, עם מיפוי בין מספור מקומי למקור
    write_markdown(slice_pages(pages, 21, 76),
                   "out/נספח א' - שומה מכרעת.md",
                   "נספח א' - שומה מכרעת",
                   source="כתב ערר + נספחים - 19.02.25.pdf", first_src_page=21)

שימוש משורת הפקודה (המרת קובץ טקסט של OCR ל-md):

    python3 export_ocr_text.py ocr.txt --out "out/כתב ערר.md" --title "כתב ערר"
    python3 export_ocr_text.py ocr.txt --out "out/נספח א'.md" --title "נספח א'" \
        --from-page 21 --to-page 76 --source "כתב ערר + נספחים.pdf"
"""

import os
import re
import sys
import argparse

PAGE_RE = re.compile(r"=====\s*PAGE\s+(\d+)\s*=====")

DISCLAIMER = ("טקסט שהופק ב-OCR. ייתכנו שגיאות זיהוי; "
              "המקור המחייב לכל ציטוט הוא קובץ ה-PDF.")


def parse_pages(text):
    """ממיר טקסט עם סמני ===== PAGE n ===== למילון {מספר עמוד: טקסט}."""
    parts = PAGE_RE.split(text)
    if len(parts) < 3:
        return {1: text}
    return {int(parts[i]): parts[i + 1] for i in range(1, len(parts), 2)}


def slice_pages(pages, first, last):
    """מחזיר תת-טווח עמודים, בשמירה על מספרי העמודים המקוריים."""
    return {p: pages[p] for p in range(first, last + 1) if p in pages}


def write_markdown(pages, out_path, title, source=None, first_src_page=None):
    """
    כותב קובץ .md עם כותרת, שורת מקור, הסתייגות OCR וסימון עמודים.
    כשהמסמך פוצל מתוך קובץ גדול, כל עמוד מקבל גם את מספרו במקור.
    """
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    keys = sorted(pages)
    lines = [f"# {title}\n"]
    if source:
        rng = f", עמודים {keys[0]}-{keys[-1]}" if keys else ""
        lines.append(f"מקור: {source}{rng}\n")
    lines.append(DISCLAIMER + "\n")

    for i, p in enumerate(keys, 1):
        if source and first_src_page:
            marker = f"===== עמוד {i} (עמוד {p} במקור) ====="
        else:
            marker = f"===== עמוד {p} ====="
        lines.append(f"\n\n{marker}\n" + pages[p].strip())

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("".join(lines))
    return out_path


def text_dir(case_root):
    """התיקייה המוסכמת לקובצי הטקסט בתוך תיק ערר."""
    return os.path.join(case_root, "ניתוח מסמכים", "טקסט OCR")


def target_for(case_root, pdf_path):
    """
    ממפה נתיב PDF בתיק לנתיב ה-md המקביל תחת "ניתוח מסמכים/טקסט OCR",
    בשמירה על מבנה תתי-התיקיות.
    """
    rel = os.path.relpath(pdf_path, case_root)
    return os.path.join(text_dir(case_root), os.path.splitext(rel)[0] + ".md")


def main():
    ap = argparse.ArgumentParser(description="ייצוא טקסט OCR לקובץ Markdown")
    ap.add_argument("txt", help="קובץ טקסט של OCR (עם סמני PAGE, אם יש)")
    ap.add_argument("--out", required=True, help="נתיב קובץ ה-md לכתיבה")
    ap.add_argument("--title", required=True)
    ap.add_argument("--source", help="שם קובץ ה-PDF שממנו פוצל המסמך")
    ap.add_argument("--from-page", type=int)
    ap.add_argument("--to-page", type=int)
    args = ap.parse_args()

    pages = parse_pages(open(args.txt, encoding="utf-8").read())
    first = None
    if args.from_page and args.to_page:
        pages = slice_pages(pages, args.from_page, args.to_page)
        first = args.from_page

    out = write_markdown(pages, args.out, args.title,
                         source=args.source, first_src_page=first)
    print(f"נשמר: {out} ({len(pages)} עמודים)", file=sys.stderr)


if __name__ == "__main__":
    main()
