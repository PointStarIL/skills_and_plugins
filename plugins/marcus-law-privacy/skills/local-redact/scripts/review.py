#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
review.py — שלב 4: שער אנושי (Human Gate).

מפיק review_preview.pdf עם המלבנים המוצעים בשקיפות (עדיין לא צרובים),
וכן review_table.txt עם "מה יושחר ולמה". שני הקבצים מקומיים ורגישים —
האדם פותח אותם, מאשר / מוריד / מוסיף, ורק אז מריצים burn.

חוק הברזל: הקבצים האלה מקומיים בלבד; המתזמר אינו קורא אותם.
"""

import os
import sys
import json
import glob
import argparse

from _common import imread_unicode, imwrite_unicode, images_to_pdf, eprint

PREVIEW_ALPHA = 0.35


def _draw_preview(img_bgr, boxes, pad=2):
    import cv2
    overlay = img_bgr.copy()
    h, w = img_bgr.shape[:2]
    for b in boxes:
        x1 = max(0, b["left"] - pad)
        y1 = max(0, b["top"] - pad)
        x2 = min(w, b["left"] + b["width"] + pad)
        y2 = min(h, b["top"] + b["height"] + pad)
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 255), -1)
    blended = cv2.addWeighted(overlay, PREVIEW_ALPHA, img_bgr, 1 - PREVIEW_ALPHA, 0)
    for b in boxes:
        x1 = max(0, b["left"] - pad)
        y1 = max(0, b["top"] - pad)
        x2 = min(w, b["left"] + b["width"] + pad)
        y2 = min(h, b["top"] + b["height"] + pad)
        cv2.rectangle(blended, (x1, y1), (x2, y2), (0, 0, 200), 2)
    return blended


def review_document(out_dir, doc, pad=2):
    import cv2
    doc_dir = os.path.join(out_dir, doc["key"])
    plan_path = os.path.join(doc_dir, "redaction_plan.json")
    pages_dir = os.path.join(doc_dir, "pages")
    if not os.path.isfile(plan_path):
        raise FileNotFoundError(f"חסר redaction_plan.json עבור {doc['filename']}")

    with open(plan_path, "r", encoding="utf-8") as f:
        plan = json.load(f)
    plan_pages = plan.get("pages", {})

    preview_dir = os.path.join(doc_dir, "_preview")
    os.makedirs(preview_dir, exist_ok=True)

    page_files = sorted(glob.glob(os.path.join(pages_dir, "page_*.png")))
    preview_paths = []
    for pf in page_files:
        base = os.path.basename(pf)
        page_num = str(int(base.replace("page_", "").replace(".png", "")))
        img = imread_unicode(pf, cv2.IMREAD_COLOR)
        if img is None:
            continue
        boxes = plan_pages.get(page_num, [])
        if boxes:
            img = _draw_preview(img, boxes, pad=pad)
        out_p = os.path.join(preview_dir, base)
        imwrite_unicode(out_p, img)
        preview_paths.append(out_p)

    preview_pdf = os.path.join(doc_dir, "review_preview.pdf")
    if preview_paths:
        images_to_pdf(preview_paths, preview_pdf)

    # טבלת "מה יושחר ולמה" (מקומית, רגישה)
    table_path = os.path.join(doc_dir, "review_table.txt")
    total = 0
    with open(table_path, "w", encoding="utf-8") as f:
        f.write(f"# {doc['filename']} — הצעת השחרה (engine={plan.get('engine')})\n")
        f.write("עמוד\tקטגוריה\tערך\n")
        for page_num in sorted(plan_pages, key=lambda x: int(x)):
            for it in plan_pages[page_num]:
                f.write(f"{page_num}\t{it['category']}\t{it.get('value','')}\n")
                total += 1

    return {"pages_previewed": len(preview_paths), "total_boxes": total,
            "preview_pdf": os.path.basename(preview_pdf) if preview_paths else None}


def load_manifest(out_dir):
    with open(os.path.join(out_dir, "manifest.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser(description="שער אנושי — preview")
    ap.add_argument("out_dir")
    ap.add_argument("--pad", type=int, default=2)
    ap.add_argument("--key", default=None)
    args = ap.parse_args()

    out_dir = os.path.abspath(args.out_dir)
    manifest = load_manifest(out_dir)
    docs = manifest["documents"]
    if args.key:
        docs = [d for d in docs if d["key"] == args.key]

    print(f"הפקת preview ל-{len(docs)} מסמכים...")
    for d in docs:
        try:
            meta = review_document(out_dir, d, pad=args.pad)
            print(f"  [OK] {d['filename']} — {meta['total_boxes']} מלבנים ב-preview")
        except Exception as e:  # noqa: BLE001
            eprint(f"  [שגיאה] {d['filename']}: {e}")
    print("\nפתח את review_preview.pdf בכל מסמך מקומית. אשר/ערוך, ואז הרץ burn.")


if __name__ == "__main__":
    main()
