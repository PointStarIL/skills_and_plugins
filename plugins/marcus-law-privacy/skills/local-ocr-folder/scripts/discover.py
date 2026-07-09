#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
discover.py — שלב 1: גילוי מסמכים בתיקייה ובניית manifest.json.

סורק רקורסיבית PDF/תמונות, מזהה לכל PDF אם הוא סרוק (תמונה) או בעל שכבת טקסט,
ובונה מניפסט של מטא-דאטה בלבד. אינו מוציא תוכן.
"""

import os
import sys
import argparse

from _common import (
    iter_source_files, doc_key, load_manifest, save_manifest,
    IMAGE_EXTS, PDF_EXTS, eprint,
)

# סף מינימלי של תווים בעמוד כדי להיחשב "בעל טקסט"
TEXT_CHARS_THRESHOLD = 20
# יחס עמודים-עם-טקסט מעליו המסמך נחשב "text" ומתחתיו "image"
TEXT_RATIO_HIGH = 0.8
TEXT_RATIO_LOW = 0.2


def analyze_pdf(path):
    """מחזיר (pages, kind, text_ratio). kind ב-{text, image, mixed}."""
    import fitz
    doc = fitz.open(path)
    try:
        pages = doc.page_count
        if pages == 0:
            return 0, "empty", 0.0
        pages_with_text = 0
        for page in doc:
            txt = page.get_text("text") or ""
            if len(txt.strip()) >= TEXT_CHARS_THRESHOLD:
                pages_with_text += 1
        ratio = pages_with_text / pages
        if ratio >= TEXT_RATIO_HIGH:
            kind = "text"
        elif ratio <= TEXT_RATIO_LOW:
            kind = "image"
        else:
            kind = "mixed"
        return pages, kind, round(ratio, 3)
    finally:
        doc.close()


def discover(root, out_dir, force=False):
    root = os.path.abspath(root)
    manifest = load_manifest(out_dir)
    manifest["root"] = root
    manifest["out_dir"] = os.path.abspath(out_dir)

    existing = {d["key"]: d for d in manifest.get("documents", [])}
    documents = []

    for path in iter_source_files(root):
        ext = os.path.splitext(path)[1].lower()
        key = doc_key(root, path)
        try:
            size = os.path.getsize(path)
        except OSError:
            size = None

        if ext in PDF_EXTS:
            try:
                pages, kind, ratio = analyze_pdf(path)
            except Exception as e:  # noqa: BLE001
                eprint(f"[discover] שגיאה בפתיחת {os.path.basename(path)}: {e}")
                pages, kind, ratio = None, "error", 0.0
        else:
            pages, kind, ratio = 1, "image", 0.0

        # מסמך זקוק ל-OCR אם אינו טקסט טהור, או אם --force
        needs_ocr = force or kind in ("image", "mixed", "empty", "error")

        doc = {
            "key": key,
            "rel_path": os.path.relpath(path, root),
            "filename": os.path.basename(path),
            "ext": ext,
            "size_bytes": size,
            "pages": pages,
            "kind": kind,
            "text_ratio": ratio,
            "needs_ocr": needs_ocr,
            "status": "pending",
        }
        # שמירה על סטטוס קודם אם קיים ולא הסתיים בכישלון
        prev = existing.get(key)
        if prev and prev.get("status") in ("done", "low_confidence"):
            doc["status"] = prev["status"]
        documents.append(doc)

    manifest["documents"] = documents
    save_manifest(out_dir, manifest)
    return manifest


def print_summary(manifest):
    docs = manifest.get("documents", [])
    print("== גילוי מסמכים ==")
    print(f"תיקייה: {manifest.get('root')}")
    print(f"נמצאו {len(docs)} קבצים.\n")
    print(f"{'#':>3}  {'עמודים':>6}  {'סוג':<7}  {'OCR':<4}  קובץ")
    for i, d in enumerate(docs, 1):
        pages = d.get("pages")
        pages_s = "?" if pages is None else str(pages)
        ocr_s = "כן" if d.get("needs_ocr") else "לא"
        print(f"{i:>3}  {pages_s:>6}  {d.get('kind',''):<7}  {ocr_s:<4}  {d.get('filename','')}")
    n_ocr = sum(1 for d in docs if d.get("needs_ocr"))
    print(f"\nמתוכם דורשים OCR: {n_ocr}. (טקסט טהור מדולג אלא אם --force)")


def main():
    ap = argparse.ArgumentParser(description="גילוי מסמכים ובניית manifest")
    ap.add_argument("folder", help="נתיב לתיקיית המסמכים")
    ap.add_argument("--out", default=None, help="תיקיית פלט (ברירת מחדל: <folder>/_ocr_out)")
    ap.add_argument("--force", action="store_true", help="סמן גם מסמכי טקסט טהור ל-OCR")
    args = ap.parse_args()

    out_dir = args.out or os.path.join(args.folder, "_ocr_out")
    manifest = discover(args.folder, out_dir, force=args.force)
    print_summary(manifest)


if __name__ == "__main__":
    main()
