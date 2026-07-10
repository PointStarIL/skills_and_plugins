#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
map_boxes.py — שלב 3: מיפוי ישויות למיקומים (bounding boxes) לפי ה-TSV.

מקורות הישויות:
  - Gemma  : entities.json (כאשר engine ב-{gemma, both})
  - regex  : תבניות מובנות (כאשר engine ב-{regex, both}) — ראה references/redaction-patterns.md
  - names  : רשימת מונחים לכפיית השחרה
מחסיר מונחי allowlist. מפיק redaction_plan.json (מקומי, רגיש).
"""

import os
import re
import sys
import json
import argparse

from _common import (
    read_tsv, rows_by_page, group_lines, find_entity_boxes, _bbox, eprint,
    normalize_heb,
)

# ---- תבניות regex (מנוע ה-fallback) ----
PHONE_RE = re.compile(r"(?:\+?972[-\s.]?|0)(?:\d[-\s.]?){7,9}\d")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
IBAN_RE = re.compile(r"IL\d{2}(?:[\s]?\d){16,20}", re.IGNORECASE)
CREDIT_RE = re.compile(r"\b\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{2,4}\b")
PLATE_RE = re.compile(r"\b\d{2,3}-\d{2,3}-\d{2,3}\b")
DATE_RE = re.compile(r"\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b")
ID_CANDIDATE_RE = re.compile(r"\d{5,9}")
# תוויות ת"ז — בודקים נוכחות מילת-מפתח בלבד (עמיד לכיוון RTL: "מספר זהות" מופיע
# בשורה המשוחזרת כ-"זהות מספר", לכן לא מסתמכים על סדר המילים).
ID_LABEL_RE = re.compile(r'(זהות|תעודת|ת["״\'.\s]?ז|ז["״\'.\s]?ת)')


def israeli_id_valid(num):
    s = "".join(ch for ch in num if ch.isdigit())
    if not (5 <= len(s) <= 9):
        return False
    s = s.zfill(9)
    total = 0
    for i, ch in enumerate(s):
        d = int(ch) * (1 if i % 2 == 0 else 2)
        total += d if d < 10 else d - 9
    return total % 10 == 0


def read_terms(path):
    if not path or not os.path.isfile(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            t = line.strip()
            if t and not t.startswith("#"):
                out.append(t)
    return out


def _line_string(line):
    """מחזיר (text, spans) — מחרוזת השורה וטווחי התווים של כל מילה."""
    parts = []
    spans = []
    pos = 0
    for r in line:
        w = r["text"]
        spans.append((pos, pos + len(w)))
        parts.append(w)
        pos += len(w) + 1  # רווח מפריד
    return " ".join(parts), spans


def _rows_in_span(line, spans, a, b):
    return [line[i] for i, (s, e) in enumerate(spans) if s < b and e > a]


def regex_boxes(lines, enable_dates=False):
    """מפיק תיבות regex לשורות עמוד. מחזיר רשימת (box, category, value)."""
    results = []

    def add(rows, category, value):
        if rows:
            results.append((_bbox(rows), category, value))

    for line in lines:
        text, spans = _line_string(line)

        for m in PHONE_RE.finditer(text):
            digits = sum(ch.isdigit() for ch in m.group())
            if digits >= 9:
                add(_rows_in_span(line, spans, m.start(), m.end()), "PHONE", m.group())
        for m in EMAIL_RE.finditer(text):
            add(_rows_in_span(line, spans, m.start(), m.end()), "EMAIL", m.group())
        for m in IBAN_RE.finditer(text):
            add(_rows_in_span(line, spans, m.start(), m.end()), "IBAN", m.group())
        for m in CREDIT_RE.finditer(text):
            add(_rows_in_span(line, spans, m.start(), m.end()), "CREDIT_CARD", m.group())
        for m in PLATE_RE.finditer(text):
            add(_rows_in_span(line, spans, m.start(), m.end()), "CAR_PLATE", m.group())
        if enable_dates:
            for m in DATE_RE.finditer(text):
                add(_rows_in_span(line, spans, m.start(), m.end()), "DATE", m.group())

        # ת"ז — ספרת ביקורת (8-9 ספרות, כולל בלי אפס מוביל) או תווית סמוכה משני הצדדים
        for m in ID_CANDIDATE_RE.finditer(text):
            digits = m.group()
            a, b = max(0, m.start() - 18), min(len(text), m.end() + 18)
            context = text[a:m.start()] + " " + text[m.end():b]  # לפני ואחרי (RTL)
            has_label = bool(ID_LABEL_RE.search(context))
            valid_id = len(digits) in (8, 9) and israeli_id_valid(digits)
            if valid_id or has_label:
                add(_rows_in_span(line, spans, m.start(), m.end()), "ISRAELI_ID", digits)

    return results


def _overlap_ratio(a, b):
    ax2, ay2 = a["left"] + a["width"], a["top"] + a["height"]
    bx2, by2 = b["left"] + b["width"], b["top"] + b["height"]
    ix = max(0, min(ax2, bx2) - max(a["left"], b["left"]))
    iy = max(0, min(ay2, by2) - max(a["top"], b["top"]))
    inter = ix * iy
    if inter == 0:
        return 0.0
    return inter / min(a["width"] * a["height"], b["width"] * b["height"])


def _dedupe(items):
    """items: list of dict {left,top,width,height,category,value}. ממזג חופפים."""
    kept = []
    for it in sorted(items, key=lambda x: -x["width"] * x["height"]):
        if any(_overlap_ratio(it, k) > 0.6 for k in kept):
            continue
        kept.append(it)
    return kept


def map_document(out_dir, doc, engine="both", names=None, allowlist=None,
                 enable_dates=False, threshold=0.82):
    doc_dir = os.path.join(out_dir, doc["key"])
    tsv_path = os.path.join(doc_dir, "words.tsv")
    if not os.path.isfile(tsv_path):
        raise FileNotFoundError(f"חסר words.tsv עבור {doc['filename']}")

    rows = read_tsv(tsv_path)
    pages = rows_by_page(rows)
    names = names or []
    allowlist = allowlist or []

    use_gemma = engine in ("gemma", "both")
    use_regex = engine in ("regex", "both")

    entities = {}
    if use_gemma:
        ent_path = os.path.join(doc_dir, "entities.json")
        if os.path.isfile(ent_path):
            with open(ent_path, "r", encoding="utf-8") as f:
                entities = json.load(f).get("pages", {})
        else:
            eprint(f"  [אזהרה] אין entities.json ל-{doc['filename']} — דילוג על Gemma")

    # פרופגציה בין-עמודית: זהות הלקוח שזוהתה בעמוד אחד (שם/ת"ז/כתובת/חשבון)
    # תוחל על כל העמודים — מכסה מקרים שבהם Gemma פספס מופע בעמוד מסוים.
    propagated = []
    if use_gemma:
        seen = set()
        for ents in entities.values():
            for e in ents:
                if e.get("type") in ("name", "id", "address", "account"):
                    t = (e.get("text") or "").strip()
                    k = normalize_heb(t)
                    if t and len(k) >= 4 and k not in seen:
                        seen.add(k)
                        propagated.append((t, e.get("type", "other").upper()))

    plan_pages = {}
    counts = {}

    for page_num, page_rows in pages.items():
        lines = group_lines(page_rows)
        items = []

        if use_gemma:
            for ent in entities.get(str(page_num), []):
                for box in find_entity_boxes(ent["text"], lines, threshold):
                    items.append({**box, "category": ent.get("type", "other").upper(),
                                  "value": ent["text"]})
            # החלת הזהות הגלובלית על עמוד זה (dedupe בהמשך מונע כפילות)
            for term, cat in propagated:
                for box in find_entity_boxes(term, lines, threshold):
                    items.append({**box, "category": cat, "value": term})

        if use_regex:
            for box, cat, val in regex_boxes(lines, enable_dates=enable_dates):
                items.append({**box, "category": cat, "value": val})

        for term in names:
            for box in find_entity_boxes(term, lines, threshold):
                items.append({**box, "category": "NAME", "value": term})

        # החסרת allowlist
        if allowlist:
            allow_boxes = []
            for term in allowlist:
                allow_boxes.extend(find_entity_boxes(term, lines, threshold))
            items = [it for it in items
                     if not any(_overlap_ratio(it, ab) > 0.5 for ab in allow_boxes)]

        items = _dedupe(items)
        if items:
            plan_pages[str(page_num)] = items
            for it in items:
                counts[it["category"]] = counts.get(it["category"], 0) + 1

    plan = {"key": doc["key"], "filename": doc["filename"],
            "engine": engine, "pages": plan_pages}
    with open(os.path.join(doc_dir, "redaction_plan.json"), "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    total = sum(counts.values())
    return {"total": total, "by_category": counts,
            "pages_with_redactions": len(plan_pages)}


def load_manifest(out_dir):
    with open(os.path.join(out_dir, "manifest.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser(description="מיפוי ישויות למלבנים")
    ap.add_argument("out_dir")
    ap.add_argument("--engine", choices=["gemma", "regex", "both"], default="both")
    ap.add_argument("--names", default=None)
    ap.add_argument("--allowlist", default=None)
    ap.add_argument("--enable-dates", action="store_true")
    ap.add_argument("--key", default=None)
    args = ap.parse_args()

    out_dir = os.path.abspath(args.out_dir)
    manifest = load_manifest(out_dir)
    docs = manifest["documents"]
    if args.key:
        docs = [d for d in docs if d["key"] == args.key]

    names = read_terms(args.names)
    allowlist = read_terms(args.allowlist)

    print(f"מיפוי מלבנים ל-{len(docs)} מסמכים (engine={args.engine})...")
    for d in docs:
        try:
            meta = map_document(out_dir, d, engine=args.engine, names=names,
                                allowlist=allowlist, enable_dates=args.enable_dates)
            by = ", ".join(f"{k}:{v}" for k, v in meta["by_category"].items()) or "אין"
            print(f"  [OK] {d['filename']} — {meta['total']} מלבנים ({by})")
        except Exception as e:  # noqa: BLE001
            eprint(f"  [שגיאה] {d['filename']}: {e}")


if __name__ == "__main__":
    main()
