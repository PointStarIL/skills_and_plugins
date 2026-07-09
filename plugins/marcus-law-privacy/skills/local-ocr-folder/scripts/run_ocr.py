#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_ocr.py — שלב 3: הרצת Tesseract והפקת שלושה פורמטים לכל מסמך.

מפיק מאותה הרצה:
  a. text.txt        — טקסט נקי (לניתוח שלך בהמשך, מקומית).
  b. searchable.pdf  — PDF עם שכבת טקסט מעל התמונה.
  c. words.tsv       — תיבות מילים (bounding boxes) + ציון ביטחון. *** הגשר להשחרה ***

מסמכי טקסט טהור (kind=text ללא --force) עוברים חילוץ ישיר משכבת הטקסט (fitz),
כך שגם עבורם נוצר TSV אחיד — בלי OCR ובלי לחשוף תוכן למודל.

הפלט נכתב לקבצים מקומיים בלבד. ל-stdout נכתב רק מטא-דאטה.
"""

import os
import sys
import csv
import argparse

from _common import (
    resolve_tesseract, load_manifest, save_manifest, PDF_EXTS, eprint,
)
from preprocess import render_pdf_page

TSV_HEADER = ["page", "left", "top", "width", "height", "conf", "text"]


def _write_tsv(tsv_path, rows):
    with open(tsv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(TSV_HEADER)
        w.writerows(rows)


def ocr_from_images(pages_dir, lang):
    """OCR על תמונות עמודים מוכנות. מחזיר (text, tsv_rows, page_confs, page_pdf_bytes)."""
    import pytesseract
    from pytesseract import Output
    from PIL import Image

    resolve_tesseract()
    page_files = sorted(
        f for f in os.listdir(pages_dir)
        if f.lower().startswith("page_") and f.lower().endswith(".png")
    )

    text_parts = []
    tsv_rows = []
    page_confs = []
    page_pdf_bytes = []

    for idx, fn in enumerate(page_files, 1):
        img = Image.open(os.path.join(pages_dir, fn))

        # a. טקסט נקי
        text_parts.append(pytesseract.image_to_string(img, lang=lang))

        # c. תיבות מילים + ביטחון
        data = pytesseract.image_to_data(img, lang=lang, output_type=Output.DICT)
        confs = []
        n = len(data["text"])
        for i in range(n):
            word = (data["text"][i] or "").strip()
            if not word:
                continue
            try:
                conf = float(data["conf"][i])
            except (ValueError, TypeError):
                conf = -1.0
            if conf < 0:
                continue
            confs.append(conf)
            tsv_rows.append([
                idx, data["left"][i], data["top"][i],
                data["width"][i], data["height"][i],
                int(round(conf)), word,
            ])
        page_confs.append(round(sum(confs) / len(confs), 1) if confs else 0.0)

        # b. עמוד searchable
        page_pdf_bytes.append(
            pytesseract.image_to_pdf_or_hocr(img, lang=lang, extension="pdf")
        )

    text = "\f".join(text_parts)
    return text, tsv_rows, page_confs, page_pdf_bytes


def native_extract(src_path, pages_dir, dpi):
    """חילוץ ישיר משכבת טקסט של PDF. מחזיר (text, tsv_rows, page_confs)."""
    import fitz
    import cv2
    from _common import imwrite_unicode

    os.makedirs(pages_dir, exist_ok=True)
    doc = fitz.open(src_path)
    scale = dpi / 72.0
    text_parts = []
    tsv_rows = []
    page_confs = []
    try:
        for i, page in enumerate(doc, 1):
            text_parts.append(page.get_text("text"))
            # שמור תמונת עמוד (עבור ההשחרה בהמשך)
            bgr = render_pdf_page(page, dpi)
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            imwrite_unicode(os.path.join(pages_dir, f"page_{i:04d}.png"), gray)
            # מילים + תיבות (בנקודות PDF -> פיקסלים)
            for w in page.get_text("words"):
                x0, y0, x1, y1, word = w[0], w[1], w[2], w[3], w[4]
                if not word.strip():
                    continue
                tsv_rows.append([
                    i, int(x0 * scale), int(y0 * scale),
                    int((x1 - x0) * scale), int((y1 - y0) * scale),
                    100, word,
                ])
            page_confs.append(100.0)
    finally:
        doc.close()
    text = "\f".join(text_parts)
    return text, tsv_rows, page_confs


def build_searchable_pdf(page_pdf_bytes, out_path):
    import fitz
    combined = fitz.open()
    try:
        for pb in page_pdf_bytes:
            src = fitz.open("pdf", pb)
            combined.insert_pdf(src)
            src.close()
        combined.save(out_path)
    finally:
        combined.close()


def run_ocr_document(root, out_dir, doc, lang="heb+eng", dpi=300):
    """מריץ OCR/חילוץ למסמך אחד. מחזיר מטא-דאטה בלבד (ללא תוכן)."""
    doc_dir = os.path.join(out_dir, doc["key"])
    pages_dir = os.path.join(doc_dir, "pages")
    os.makedirs(doc_dir, exist_ok=True)

    txt_path = os.path.join(doc_dir, "text.txt")
    tsv_path = os.path.join(doc_dir, "words.tsv")
    searchable_path = os.path.join(doc_dir, "searchable.pdf")
    src_path = os.path.join(root, doc["rel_path"])

    if doc.get("needs_ocr", True):
        if not os.path.isdir(pages_dir) or not os.listdir(pages_dir):
            raise RuntimeError("חסרות תמונות עמודים — הרץ preprocess תחילה")
        text, tsv_rows, page_confs, page_pdf_bytes = ocr_from_images(pages_dir, lang)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)
        _write_tsv(tsv_path, tsv_rows)
        build_searchable_pdf(page_pdf_bytes, searchable_path)
        method = "ocr"
    else:
        text, tsv_rows, page_confs = native_extract(src_path, pages_dir, dpi)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)
        _write_tsv(tsv_path, tsv_rows)
        # מסמך טקסט כבר searchable — העתק את המקור
        if doc["ext"].lower() in PDF_EXTS:
            import shutil
            shutil.copyfile(src_path, searchable_path)
        method = "native"

    return {
        "method": method,
        "pages": len(page_confs),
        "page_confidence": page_confs,
        "word_count": len(tsv_rows),
        "outputs": {
            "text": os.path.relpath(txt_path, out_dir),
            "tsv": os.path.relpath(tsv_path, out_dir),
            "searchable_pdf": os.path.relpath(searchable_path, out_dir)
                             if os.path.exists(searchable_path) else None,
        },
    }


def main():
    ap = argparse.ArgumentParser(description="הרצת OCR והפקת TXT/PDF/TSV")
    ap.add_argument("folder", help="נתיב לתיקיית המסמכים (root)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--lang", default="heb+eng")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--key", default=None, help="עבד רק מסמך בעל key זה")
    args = ap.parse_args()

    root = os.path.abspath(args.folder)
    out_dir = args.out or os.path.join(root, "_ocr_out")
    manifest = load_manifest(out_dir)

    targets = manifest["documents"]
    if args.key:
        targets = [d for d in targets if d["key"] == args.key]

    print(f"הרצת OCR ל-{len(targets)} מסמכים (שפות: {args.lang})...")
    for d in targets:
        if d.get("status") == "failed":
            continue
        try:
            meta = run_ocr_document(root, out_dir, d, lang=args.lang, dpi=args.dpi)
            d["ocr"] = meta
            print(f"  [OK] {d['filename']} — {meta['pages']} עמ', {meta['word_count']} מילים ({meta['method']})")
        except Exception as e:  # noqa: BLE001
            d["status"] = "failed"
            d["error"] = str(e)
            eprint(f"  [שגיאה] {d['filename']}: {e}")

    save_manifest(out_dir, manifest)


if __name__ == "__main__":
    main()
