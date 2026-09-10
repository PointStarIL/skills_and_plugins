#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_redaction.py — שלב אימות אחרי צריבה.

מוודא שכל ערך מזהה שזוהה (שם/ת"ז/כתובת/חשבון) אכן אינו קריא ב-redacted.txt
שהצריבה הפיקה. אם ערך כזה עדיין מופיע כטקסט גלוי (לא █) — זו "שארית" שיש
להתריע עליה (הסתרה שפוספסה / מלבן שלא כיסה). הפלט: JSON ל-stdout בלבד.

חוק הברזל נשמר: הקבצים מקומיים; רק מטא-דאטה (ספירות + מספרי עמוד) חוזר.
"""

import os
import sys
import json
import argparse

from _common import normalize_heb, eprint

IDENT_TYPES = {"name", "id", "address", "account"}
IDENT_CATS = {"NAME", "ID", "ISRAELI_ID", "ADDRESS", "ACCOUNT", "MANUAL"}


def _sensitive_values(doc_dir):
    """אוסף את הערכים המזהים שהיו אמורים להיות מוסתרים (מ-Gemma ומהתוכנית)."""
    vals = set()
    ep = os.path.join(doc_dir, "entities.json")
    if os.path.isfile(ep):
        with open(ep, encoding="utf-8") as f:
            for ents in json.load(f).get("pages", {}).values():
                for e in ents:
                    if e.get("type") in IDENT_TYPES and str(e.get("text", "")).strip():
                        vals.add(str(e["text"]).strip())
    pp = os.path.join(doc_dir, "redaction_plan.json")
    if os.path.isfile(pp):
        with open(pp, encoding="utf-8") as f:
            for boxes in json.load(f).get("pages", {}).values():
                for b in boxes:
                    if b.get("category") in IDENT_CATS and str(b.get("value", "")).strip():
                        vals.add(str(b["value"]).strip())
    # רק ערכים בעלי מספיק "חתימה" (למנוע התאמות שווא קצרות)
    return [v for v in vals if len(normalize_heb(v)) >= 4]


def verify_document(out_dir, doc):
    doc_dir = os.path.join(out_dir, doc["key"])
    rp = os.path.join(doc_dir, "redacted.txt")
    if not os.path.isfile(rp):
        return {"checked": 0, "residuals": [], "note": "אין redacted.txt (לא נצרב)"}
    with open(rp, encoding="utf-8") as f:
        text = f.read()
    values = _sensitive_values(doc_dir)
    residuals = []
    for i, page_text in enumerate(text.split("\f"), 1):
        # טקסט גלוי = מילים שאינן מכילות █ (הצריבה מחליפה מילה מוסתרת ב-█)
        visible = normalize_heb(" ".join(t for t in page_text.split() if "█" not in t))
        for v in values:
            nv = normalize_heb(v)
            if nv and nv in visible:
                residuals.append({"page": i, "value": v[:60]})
    # dedupe (value, page)
    seen = set()
    uniq = []
    for r in residuals:
        k = (r["page"], r["value"])
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    return {"checked": len(values), "residuals": uniq}


def main():
    ap = argparse.ArgumentParser(description="אימות שאריות אחרי צריבה")
    ap.add_argument("out_dir")
    ap.add_argument("--key", default=None)
    ap.add_argument("--show-values", action="store_true",
                    help="הצג את ערכי השאריות עצמם. לשימוש אנושי מקומי בלבד: "
                         "הערכים הם תוכן רגיש ואסור שייכנסו להקשר של מודל.")
    args = ap.parse_args()
    out_dir = os.path.abspath(args.out_dir)
    with open(os.path.join(out_dir, "manifest.json"), encoding="utf-8") as f:
        docs = json.load(f)["documents"]
    if args.key:
        docs = [d for d in docs if d["key"] == args.key]
    result = {"documents": []}
    for d in docs:
        try:
            r = verify_document(out_dir, d)
        except Exception as e:  # noqa: BLE001
            eprint(f"  [שגיאה] אימות {d['filename']}: {e}")
            r = {"checked": 0, "residuals": [], "error": str(e)}
        if not args.show_values:
            # ברירת המחדל: ספירה ומספרי עמודים בלבד, בלי ערכים.
            r = dict(r)
            r["pages"] = sorted({x["page"] for x in r.get("residuals", [])})
            r["residuals"] = len(r.get("residuals", []))
        result["documents"].append({"key": d["key"], "filename": d["filename"], **r})
    result["total_residuals"] = sum(
        d["residuals"] if isinstance(d.get("residuals"), int) else len(d.get("residuals", []))
        for d in result["documents"]
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
