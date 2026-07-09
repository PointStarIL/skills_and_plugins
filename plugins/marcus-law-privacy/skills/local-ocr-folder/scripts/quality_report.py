#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
quality_report.py — שלב 4: בקרת איכות ודגלים לעיון אנושי.

מחשב ציון ביטחון ממוצע לעמוד ולמסמך, מסמן עמודים מתחת לסף כ-needs_human_review,
מעדכן את הסטטוס במניפסט (done / low_confidence / failed), ומפיק quality_report.json.

מטא-דאטה בלבד — לעולם לא תוכן.
"""

import os
import sys
import json
import argparse

from _common import load_manifest, save_manifest, manifest_path


def build_report(manifest, threshold=75.0):
    rows = []
    for d in manifest["documents"]:
        entry = {
            "key": d["key"],
            "filename": d["filename"],
            "pages": d.get("pages"),
            "kind": d.get("kind"),
            "status": d.get("status", "pending"),
            "mean_confidence": None,
            "low_pages": [],
        }

        if d.get("status") == "failed":
            entry["error"] = d.get("error", "")
            rows.append(entry)
            continue

        ocr = d.get("ocr")
        if not ocr:
            rows.append(entry)
            continue

        confs = ocr.get("page_confidence", []) or []
        if confs:
            mean = round(sum(confs) / len(confs), 1)
            entry["mean_confidence"] = mean
            entry["low_pages"] = [i + 1 for i, c in enumerate(confs) if c < threshold]
            if ocr.get("method") == "native":
                new_status = "done"
            elif entry["low_pages"]:
                new_status = "low_confidence"
            else:
                new_status = "done"
            d["status"] = new_status
            entry["status"] = new_status
        rows.append(entry)

    report = {
        "out_dir": manifest.get("out_dir"),
        "threshold": threshold,
        "documents": rows,
        "totals": {
            "documents": len(rows),
            "done": sum(1 for r in rows if r["status"] == "done"),
            "low_confidence": sum(1 for r in rows if r["status"] == "low_confidence"),
            "failed": sum(1 for r in rows if r["status"] == "failed"),
            "pending": sum(1 for r in rows if r["status"] == "pending"),
        },
    }
    return report


def print_report(report):
    print("== דוח איכות OCR ==")
    print(f"סף לעיון אנושי: {report['threshold']}%\n")
    print(f"{'#':>3}  {'עמ':>3}  {'ביטחון':>7}  {'סטטוס':<15}  קובץ")
    for i, r in enumerate(report["documents"], 1):
        conf = r["mean_confidence"]
        conf_s = "-" if conf is None else f"{conf:.0f}%"
        flag = f"  ⚑ עמ' {r['low_pages']}" if r["low_pages"] else ""
        print(f"{i:>3}  {str(r.get('pages','?')):>3}  {conf_s:>7}  {r['status']:<15}  {r['filename']}{flag}")
    t = report["totals"]
    print(f"\nסה\"כ: {t['documents']} | הושלם: {t['done']} | ביטחון נמוך: {t['low_confidence']} | נכשל: {t['failed']} | ממתין: {t['pending']}")
    if t["low_confidence"]:
        print("עמודים בביטחון נמוך מסומנים ⚑ ומומלצים לעיון אנושי לפני השחרה.")


def main():
    ap = argparse.ArgumentParser(description="דוח איכות OCR")
    ap.add_argument("folder", help="נתיב לתיקיית המסמכים (root)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--threshold", type=float, default=75.0)
    args = ap.parse_args()

    root = os.path.abspath(args.folder)
    out_dir = args.out or os.path.join(root, "_ocr_out")
    manifest = load_manifest(out_dir)

    report = build_report(manifest, threshold=args.threshold)
    save_manifest(out_dir, manifest)
    with open(os.path.join(out_dir, "quality_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print_report(report)


if __name__ == "__main__":
    main()
