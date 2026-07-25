#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
הטמעת שכבת טקסט (OCR text layer) בקובצי PDF סרוקים.

למה זה נחוץ: OCR רגיל מחזיר טקסט לתוך הסשן בלבד; קובץ ה-PDF שנשמר אצל
המשתמש נשאר תמונה, ולכן לא ניתן לחפש בו, לסמן או להעתיק ממנו. הסקריפט
מריץ ocrmypdf עם Tesseract עברית ומטמיע שכבת טקסט בלתי נראית מתחת לסריקה.
המראה של המסמך אינו משתנה.

שימוש:
    # קובץ בודד
    python3 embed_text_layer.py "file.pdf" --out "file_ocr.pdf"

    # תיקייה שלמה, במקום (עיבוד לקובץ זמני והחלפה)
    python3 embed_text_layer.py "תיקיית ערר" --recursive --in-place

    # תיקייה שלמה, לתיקיית פלט נפרדת ששומרת על מבנה התיקיות
    python3 embed_text_layer.py "תיקיית ערר" --recursive --out-dir /tmp/ocr

דגלים שימושיים:
    --skip-existing   דלג על קבצים שכבר יש בהם שכבת טקסט (ברירת מחדל)
    --force           הרץ מחדש גם על קבצים שיש בהם טקסט (--redo-ocr)
    --jobs N          מספר תהליכונים ל-Tesseract (ברירת מחדל: מספר הליבות)

דרישות: ocrmypdf, tesseract-ocr, tesseract-ocr-heb, poppler-utils, pypdf
    pip install ocrmypdf pypdf --break-system-packages
    apt-get install -y tesseract-ocr-heb
"""

import os
import sys
import shutil
import argparse
import subprocess
import tempfile

LANG = "heb+eng"


def has_text_layer(pdf_path, min_words=10):
    """האם כבר קיימת שכבת טקסט משמעותית בקובץ."""
    try:
        from pypdf import PdfReader
        r = PdfReader(pdf_path)
        words = 0
        for p in r.pages[:5]:
            words += len((p.extract_text() or "").split())
            if words >= min_words:
                return True
        return words >= min_words
    except Exception:
        return False


def page_count(pdf_path):
    try:
        from pypdf import PdfReader
        return len(PdfReader(pdf_path).pages)
    except Exception:
        return 0


def embed(src, dst, lang=LANG, jobs=None, force=False, quiet=True):
    """מריץ ocrmypdf על קובץ בודד. מחזיר (ok, message)."""
    cmd = ["ocrmypdf", "-l", lang, "--output-type", "pdf"]
    cmd.append("--redo-ocr" if force else "--skip-text")
    if jobs:
        cmd += ["--jobs", str(jobs)]
    if quiet:
        cmd.append("--quiet")
    cmd += [src, dst]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
    except subprocess.TimeoutExpired:
        return False, "פסק זמן"
    if p.returncode != 0:
        return False, (p.stderr or "").strip().splitlines()[-1:] or ["שגיאה לא ידועה"]
    return True, "ok"


def iter_pdfs(root, recursive):
    if os.path.isfile(root):
        yield root
        return
    if recursive:
        for d, _, files in os.walk(root):
            # מדלגים על תיקיות עבודה פנימיות
            if os.path.basename(d).startswith(("_", ".")):
                continue
            for f in sorted(files):
                if f.lower().endswith(".pdf"):
                    yield os.path.join(d, f)
    else:
        for f in sorted(os.listdir(root)):
            if f.lower().endswith(".pdf"):
                yield os.path.join(root, f)


def main():
    ap = argparse.ArgumentParser(description="הטמעת שכבת טקסט בקובצי PDF סרוקים")
    ap.add_argument("path", help="קובץ PDF או תיקייה")
    ap.add_argument("--out", help="קובץ פלט (רק כשהקלט הוא קובץ בודד)")
    ap.add_argument("--out-dir", help="תיקיית פלט; מבנה התיקיות נשמר")
    ap.add_argument("--in-place", action="store_true", help="החלפת הקבצים במקום")
    ap.add_argument("--recursive", action="store_true", help="סריקת תתי-תיקיות")
    ap.add_argument("--force", action="store_true", help="הרצה מחדש גם על קבצים עם טקסט")
    ap.add_argument("--lang", default=LANG)
    ap.add_argument("--jobs", type=int, default=None)
    args = ap.parse_args()

    if not (args.out or args.out_dir or args.in_place):
        ap.error("נדרש אחד מ: --out / --out-dir / --in-place")

    files = list(iter_pdfs(args.path, args.recursive))
    if not files:
        print("לא נמצאו קובצי PDF", file=sys.stderr)
        return 1

    done, skipped, failed = [], [], []
    for src in files:
        rel = os.path.relpath(src, args.path if os.path.isdir(args.path) else os.path.dirname(src))
        if not args.force and has_text_layer(src):
            skipped.append(rel)
            print(f"[דילוג] כבר יש שכבת טקסט: {rel}", file=sys.stderr)
            continue

        n = page_count(src)
        print(f"[OCR] {rel} ({n} עמ')...", file=sys.stderr)

        if args.out:
            dst = args.out
        elif args.out_dir:
            dst = os.path.join(args.out_dir, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
        else:
            fd, dst = tempfile.mkstemp(suffix=".pdf")
            os.close(fd)

        ok, msg = embed(src, dst, lang=args.lang, jobs=args.jobs, force=args.force)
        if not ok:
            failed.append((rel, msg))
            print(f"[כשל] {rel}: {msg}", file=sys.stderr)
            if args.in_place and os.path.exists(dst):
                os.remove(dst)
            continue

        # אימות: לא איבדנו עמודים
        if n and page_count(dst) != n:
            failed.append((rel, "מספר העמודים השתנה"))
            print(f"[כשל] {rel}: מספר העמודים השתנה", file=sys.stderr)
            continue

        if args.in_place:
            shutil.move(dst, src)
        done.append(rel)

    print(f"\nהוטמעה שכבת טקסט: {len(done)} | דילוגים: {len(skipped)} | כשלים: {len(failed)}",
          file=sys.stderr)
    for rel, msg in failed:
        print(f"  כשל: {rel} ({msg})", file=sys.stderr)
    return 0 if not failed else 2


if __name__ == "__main__":
    sys.exit(main())
