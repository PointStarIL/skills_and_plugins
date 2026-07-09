#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ocr_folder.py — entrypoint: מריץ את כל שרשרת ה-OCR על תיקייה.

discover -> preprocess -> run_ocr -> quality_report

הפלט נכתב מקומית לתיקיית <folder>/_ocr_out.
ל-stdout נכתב רק מטא-דאטה (טבלת סטטוס). המודל שמריץ סקריפט זה לעולם
אינו רואה תוכן מסמך — רק את דוח האיכות.

שימוש:
    python ocr_folder.py "<נתיב לתיקייה>" [--out DIR] [--lang heb+eng]
                         [--dpi 300] [--threshold 75] [--force]
"""

import os
import sys
import argparse

from _common import load_manifest, save_manifest, eprint
import discover as discover_mod
import preprocess as preprocess_mod
import run_ocr as run_ocr_mod
import quality_report as quality_mod


def main():
    ap = argparse.ArgumentParser(description="שרשרת OCR מקומית מלאה על תיקייה")
    ap.add_argument("folder", help="נתיב לתיקיית המסמכים")
    ap.add_argument("--out", default=None, help="תיקיית פלט (ברירת מחדל: <folder>/_ocr_out)")
    ap.add_argument("--lang", default="heb+eng", help="שפות Tesseract (למשל heb+heb_old+eng)")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--threshold", type=float, default=75.0)
    ap.add_argument("--force", action="store_true", help="הרץ OCR גם על PDF עם שכבת טקסט")
    args = ap.parse_args()

    root = os.path.abspath(args.folder)
    if not os.path.isdir(root):
        eprint(f"שגיאה: התיקייה לא קיימת: {root}")
        sys.exit(2)
    out_dir = args.out or os.path.join(root, "_ocr_out")
    os.makedirs(out_dir, exist_ok=True)

    # שלב 1: גילוי
    eprint("== שלב 1/4: גילוי מסמכים ==")
    manifest = discover_mod.discover(root, out_dir, force=args.force)
    eprint(f"נמצאו {len(manifest['documents'])} קבצים.")

    # שלב 2: עיבוד מקדים
    eprint("== שלב 2/4: עיבוד מקדים ==")
    for d in manifest["documents"]:
        if not d.get("needs_ocr"):
            continue
        try:
            pm = preprocess_mod.preprocess_document(root, out_dir, d, dpi=args.dpi)
            d["page_meta"] = pm
            d["preprocessed"] = True
            eprint(f"  [OK] {d['filename']} — {len(pm)} עמודים")
        except Exception as e:  # noqa: BLE001
            d["preprocessed"] = False
            d["status"] = "failed"
            d["error"] = str(e)
            eprint(f"  [שגיאה] {d['filename']}: {e}")
    save_manifest(out_dir, manifest)

    # שלב 3: OCR
    eprint("== שלב 3/4: OCR ==")
    for d in manifest["documents"]:
        if d.get("status") == "failed":
            continue
        try:
            meta = run_ocr_mod.run_ocr_document(root, out_dir, d, lang=args.lang, dpi=args.dpi)
            d["ocr"] = meta
            eprint(f"  [OK] {d['filename']} — {meta['pages']} עמ', {meta['word_count']} מילים ({meta['method']})")
        except Exception as e:  # noqa: BLE001
            d["status"] = "failed"
            d["error"] = str(e)
            eprint(f"  [שגיאה] {d['filename']}: {e}")
    save_manifest(out_dir, manifest)

    # שלב 4: דוח איכות (הפלט היחיד ל-stdout)
    eprint("== שלב 4/4: דוח איכות ==")
    report = quality_mod.build_report(manifest, threshold=args.threshold)
    save_manifest(out_dir, manifest)
    import json
    with open(os.path.join(out_dir, "quality_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    quality_mod.print_report(report)
    print(f"\nהפלט נשמר מקומית ב: {out_dir}")
    print("שלב הבא: השחרה עם local-redact (redact_folder.py).")


if __name__ == "__main__":
    main()
