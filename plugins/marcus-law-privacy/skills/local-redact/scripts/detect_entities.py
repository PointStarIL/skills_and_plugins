#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
detect_entities.py — שלב 2: זיהוי ישויות מול Gemma המקומי.

שולח את טקסט המסמך עמוד-עמוד ל-endpoint התואם-OpenAI, ומבקש רשימת ישויות
מזהות ב-JSON מובנה. כותב entities.json מקומי לכל מסמך.

חוק הברזל: הסקריפט מדבר עם Gemma; המתזמר אינו רואה את הטקסט ולא את פלט Gemma.
"""

import os
import sys
import json
import argparse

from _common import chat_completion, extract_json, eprint

SYSTEM_PROMPT = (
    "אתה מנוע לזיהוי פרטים מזהים (PII) במסמכים משפטיים בעברית. "
    "קבל טקסט של עמוד אחד, והחזר אך ורק את הפרטים המזהים שמופיעים בו מילולית. "
    "החזר JSON תקין במבנה: {\"entities\":[{\"text\":\"...\",\"type\":\"...\"}]}. "
    "ערכי type אפשריים: name (שם אדם/חברה), id (מספר זהות/דרכון), phone (טלפון), "
    "email (דוא\"ל), address (כתובת), account (חשבון בנק/IBAN/כרטיס אשראי), "
    "case_number (מספר תיק/הליך), other. "
    "אל תמציא ערכים שאינם בטקסט. אל תוסיף הסברים. "
    "אם אין פרטים מזהים, החזר {\"entities\":[]}."
)


def load_manifest(out_dir):
    p = os.path.join(out_dir, "manifest.json")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def detect_page(page_text, retries=2):
    """שולח עמוד ל-Gemma ומחזיר רשימת ישויות. תיקון JSON + retry."""
    if not page_text.strip():
        return []
    last_err = None
    for attempt in range(retries + 1):
        try:
            content = chat_completion(SYSTEM_PROMPT, page_text, json_mode=True)
        except Exception as e:  # noqa: BLE001
            last_err = e
            continue
        obj = extract_json(content)
        if isinstance(obj, dict) and isinstance(obj.get("entities"), list):
            out = []
            for ent in obj["entities"]:
                if isinstance(ent, dict) and ent.get("text"):
                    out.append({"text": str(ent["text"]),
                                "type": str(ent.get("type", "other"))})
            return out
    if last_err:
        raise last_err
    return []


def detect_document(out_dir, doc):
    """מזהה ישויות למסמך אחד. מחזיר מטא-דאטה (ספירות בלבד)."""
    doc_dir = os.path.join(out_dir, doc["key"])
    txt_path = os.path.join(doc_dir, "text.txt")
    if not os.path.isfile(txt_path):
        raise FileNotFoundError(f"חסר text.txt עבור {doc['filename']}")

    with open(txt_path, "r", encoding="utf-8") as f:
        full = f.read()
    pages = full.split("\f")

    per_page = {}
    counts = {}
    for i, page_text in enumerate(pages, 1):
        ents = detect_page(page_text)
        per_page[str(i)] = ents
        for e in ents:
            counts[e["type"]] = counts.get(e["type"], 0) + 1

    with open(os.path.join(doc_dir, "entities.json"), "w", encoding="utf-8") as f:
        json.dump({"key": doc["key"], "pages": per_page}, f, ensure_ascii=False, indent=2)

    return {"pages": len(pages), "total": sum(counts.values()), "by_type": counts}


def main():
    ap = argparse.ArgumentParser(description="זיהוי ישויות מול Gemma")
    ap.add_argument("out_dir", help="נתיב לתיקיית _ocr_out")
    ap.add_argument("--key", default=None, help="עבד רק מסמך בעל key זה")
    args = ap.parse_args()

    out_dir = os.path.abspath(args.out_dir)
    manifest = load_manifest(out_dir)
    docs = manifest["documents"]
    if args.key:
        docs = [d for d in docs if d["key"] == args.key]

    print(f"זיהוי ישויות ל-{len(docs)} מסמכים מול Gemma...")
    for d in docs:
        try:
            meta = detect_document(out_dir, d)
            by = ", ".join(f"{k}:{v}" for k, v in meta["by_type"].items()) or "אין"
            print(f"  [OK] {d['filename']} — {meta['total']} ישויות ({by})")
        except Exception as e:  # noqa: BLE001
            eprint(f"  [שגיאה] {d['filename']}: {e}")


if __name__ == "__main__":
    main()
