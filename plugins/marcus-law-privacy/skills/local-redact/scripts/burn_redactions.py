#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
burn_redactions.py — שלב 5: צריבה בלתי-הפיכה.

מרסטר כל עמוד, צובע את המלבנים בשחור מלא, ומשטח לתמונה — כך שאין שכבת טקסט
מתחת ואי אפשר לחלץ. פלט: <שם-קובץ>.redacted.pdf בתיקיית המקור, וגם redacted.txt
(שחזור טקסט מה-TSV כשהמילים הרגישות מוחלפות ב-█) בתוך תיקיית הפלט.

הצריבה בלתי-הפיכה — עבוד על עותק. שלב זה רץ רק אחרי שער אנושי (--burn).
"""

import os
import sys
import json
import glob
import argparse

from _common import (
    imread_unicode, imwrite_unicode, images_to_pdf,
    read_tsv, rows_by_page, group_lines, eprint,
)


def _overlaps(row, box):
    ax2, ay2 = row["left"] + row["width"], row["top"] + row["height"]
    bx2, by2 = box["left"] + box["width"], box["top"] + box["height"]
    ix = max(0, min(ax2, bx2) - max(row["left"], box["left"]))
    iy = max(0, min(ay2, by2) - max(row["top"], box["top"]))
    inter = ix * iy
    area = max(1, row["width"] * row["height"])
    return inter / area > 0.3


def burn_document(out_dir, doc, root, pad=2):
    import cv2
    doc_dir = os.path.join(out_dir, doc["key"])
    plan_path = os.path.join(doc_dir, "redaction_plan.json")
    pages_dir = os.path.join(doc_dir, "pages")
    if not os.path.isfile(plan_path):
        raise FileNotFoundError(f"חסר redaction_plan.json עבור {doc['filename']}")

    with open(plan_path, "r", encoding="utf-8") as f:
        plan = json.load(f)
    plan_pages = plan.get("pages", {})

    burned_dir = os.path.join(doc_dir, "_burned")
    os.makedirs(burned_dir, exist_ok=True)

    # 1) צריבת התמונות
    page_files = sorted(glob.glob(os.path.join(pages_dir, "page_*.png")))
    burned_paths = []
    for pf in page_files:
        base = os.path.basename(pf)
        page_num = str(int(base.replace("page_", "").replace(".png", "")))
        img = imread_unicode(pf, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        h, w = img.shape[:2]
        for b in plan_pages.get(page_num, []):
            x1 = max(0, b["left"] - pad)
            y1 = max(0, b["top"] - pad)
            x2 = min(w, b["left"] + b["width"] + pad)
            y2 = min(h, b["top"] + b["height"] + pad)
            cv2.rectangle(img, (x1, y1), (x2, y2), 0, -1)  # שחור מלא
        out_p = os.path.join(burned_dir, base)
        imwrite_unicode(out_p, img)
        burned_paths.append(out_p)

    # 2) redacted.pdf בתיקיית המקור
    src_path = os.path.join(root, doc["rel_path"])
    src_dir = os.path.dirname(src_path)
    stem = os.path.splitext(os.path.basename(src_path))[0]
    redacted_pdf = os.path.join(src_dir, f"{stem}.redacted.pdf")
    if burned_paths:
        images_to_pdf(burned_paths, redacted_pdf)

    # 3) redacted.txt — שחזור טקסט עם החלפת מילים רגישות
    tsv_path = os.path.join(doc_dir, "words.tsv")
    redacted_txt = os.path.join(doc_dir, "redacted.txt")
    if os.path.isfile(tsv_path):
        rows = read_tsv(tsv_path)
        pages = rows_by_page(rows)
        with open(redacted_txt, "w", encoding="utf-8") as f:
            for page_num in sorted(pages):
                boxes = plan_pages.get(str(page_num), [])
                for line in group_lines(pages[page_num]):
                    words = []
                    for r in line:
                        if any(_overlaps(r, b) for b in boxes):
                            words.append("█" * max(1, len(r["text"])))
                        else:
                            words.append(r["text"])
                    f.write(" ".join(words) + "\n")
                f.write("\f")

    return {"pages": len(burned_paths),
            "redacted_pdf": redacted_pdf if burned_paths else None}


def load_manifest(out_dir):
    with open(os.path.join(out_dir, "manifest.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser(description="צריבה בלתי-הפיכה של ההשחרה")
    ap.add_argument("out_dir")
    ap.add_argument("--pad", type=int, default=2)
    ap.add_argument("--key", default=None)
    args = ap.parse_args()

    out_dir = os.path.abspath(args.out_dir)
    manifest = load_manifest(out_dir)
    root = manifest.get("root") or os.path.dirname(out_dir)
    docs = manifest["documents"]
    if args.key:
        docs = [d for d in docs if d["key"] == args.key]

    print(f"צריבת השחרה ל-{len(docs)} מסמכים...")
    for d in docs:
        try:
            meta = burn_document(out_dir, d, root, pad=args.pad)
            name = os.path.basename(meta["redacted_pdf"]) if meta["redacted_pdf"] else "-"
            print(f"  [OK] {d['filename']} — {meta['pages']} עמ' -> {name}")
        except Exception as e:  # noqa: BLE001
            eprint(f"  [שגיאה] {d['filename']}: {e}")
    print("\nהושלם. קובצי <שם>.redacted.pdf נשמרו לצד המקור. אמת ויזואלית לפני העלאה חיצונית.")


if __name__ == "__main__":
    main()
