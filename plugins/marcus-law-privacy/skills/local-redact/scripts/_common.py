#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_common.py — עזרי-ליבה משותפים לסקריפטי ההשחרה.

כולל: קלט/פלט תמונה עם נתיבי עברית, קריאת TSV, קיבוץ לשורות, נרמול עברית
לצורך התאמה סובלנית לשגיאות OCR, בניית PDF מושחר, ולקוח HTTP ל-Gemma (urllib).

עיקרון: אף פונקציה אינה מחזירה תוכן אל המתזמר. תוכן נשאר בקבצים מקומיים / מול Gemma.
"""

import os
import re
import sys
import json
import csv
import difflib

import numpy as np


# ---- קלט/פלט תמונה שעובד עם נתיבי עברית ב-Windows ----

def imread_unicode(path, flags=None):
    import cv2
    if flags is None:
        flags = cv2.IMREAD_GRAYSCALE
    data = np.fromfile(path, dtype=np.uint8)
    if data.size == 0:
        return None
    return cv2.imdecode(data, flags)


def imwrite_unicode(path, img, ext=".png"):
    import cv2
    ok, buf = cv2.imencode(ext, img)
    if not ok:
        raise IOError(f"encode failed for {path}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    buf.tofile(path)
    return True


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


# ---- TSV ----

def read_tsv(tsv_path):
    """קורא words.tsv ומחזיר רשימת dict לכל מילה: page,left,top,width,height,conf,text."""
    rows = []
    with open(tsv_path, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f, delimiter="\t")
        for d in r:
            try:
                rows.append({
                    "page": int(d["page"]),
                    "left": int(d["left"]),
                    "top": int(d["top"]),
                    "width": int(d["width"]),
                    "height": int(d["height"]),
                    "conf": int(float(d.get("conf", 0) or 0)),
                    "text": d["text"],
                })
            except (ValueError, KeyError):
                continue
    return rows


def rows_by_page(rows):
    pages = {}
    for r in rows:
        pages.setdefault(r["page"], []).append(r)
    return pages


def group_lines(page_rows):
    """מקבץ מילים של עמוד לשורות לפי קרבת קואורדינטת Y, שומר סדר קריאה מקורי בשורה."""
    if not page_rows:
        return []
    heights = [r["height"] for r in page_rows if r["height"] > 0]
    med_h = sorted(heights)[len(heights) // 2] if heights else 20
    tol = max(6, int(med_h * 0.6))

    indexed = list(enumerate(page_rows))
    indexed.sort(key=lambda t: (t[1]["top"], t[1]["left"]))

    lines = []
    current = []
    current_top = None
    for _, r in indexed:
        if current_top is None or abs(r["top"] - current_top) <= tol:
            current.append(r)
            current_top = r["top"] if current_top is None else current_top
        else:
            lines.append(current)
            current = [r]
            current_top = r["top"]
    if current:
        lines.append(current)
    return lines


# ---- נרמול עברית להתאמה סובלנית ----

_FINALS = {"ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ"}
_NIQQUD = re.compile(r"[֑-ׇ]")
_PUNCT = re.compile(r"[\"'`׳״.,\-–—()\[\]/\\]")


def normalize_heb(s):
    """מנרמל מחרוזת עברית/לטינית להתאמה סובלנית: מסיר ניקוד, פיסוק וגרשיים,
    מאחד אותיות סופיות, מוריד לטינית לאותיות קטנות ומכווץ רווחים."""
    if not s:
        return ""
    s = _NIQQUD.sub("", s)
    s = "".join(_FINALS.get(ch, ch) for ch in s)
    s = _PUNCT.sub("", s)
    s = s.lower()
    s = re.sub(r"\s+", "", s)
    return s


def similar(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()


def find_entity_boxes(entity_text, lines, threshold=0.82):
    """מאתר את מיקומי המילים של מחרוזת ישות בתוך שורות עמוד.
    מחזיר רשימת תיבות (left,top,width,height). סובלני לשגיאות OCR ולריבוי מילים."""
    target = normalize_heb(entity_text)
    if not target:
        return []
    boxes = []
    for line in lines:
        norms = [normalize_heb(r["text"]) for r in line]
        n = len(line)
        i = 0
        while i < n:
            # התאמת מילה בודדת
            if norms[i] and (norms[i] == target or
                             (len(target) >= 4 and similar(norms[i], target) >= threshold)):
                boxes.append(_bbox([line[i]]))
                i += 1
                continue
            # התאמת רצף מילים סמוכות (שם מלא / כתובת / מספר מפוצל)
            matched = False
            acc = ""
            for j in range(i, min(i + 8, n)):
                acc += norms[j]
                if len(acc) < len(target) * 0.6:
                    continue
                if acc == target or similar(acc, target) >= threshold:
                    boxes.append(_bbox(line[i:j + 1]))
                    i = j + 1
                    matched = True
                    break
                if len(acc) > len(target) * 1.4:
                    break
            if not matched:
                i += 1
    return boxes


def _bbox(rows):
    left = min(r["left"] for r in rows)
    top = min(r["top"] for r in rows)
    right = max(r["left"] + r["width"] for r in rows)
    bottom = max(r["top"] + r["height"] for r in rows)
    return {"left": left, "top": top, "width": right - left, "height": bottom - top}


# ---- ציור והפקת PDF ----

def draw_boxes(img, boxes, pad=2, color=0, filled=True):
    """מצייר מלבנים על תמונת OpenCV. color=0 שחור. מחזיר עותק."""
    import cv2
    out = img.copy()
    h, w = out.shape[:2]
    thickness = -1 if filled else 2
    for b in boxes:
        x1 = max(0, b["left"] - pad)
        y1 = max(0, b["top"] - pad)
        x2 = min(w, b["left"] + b["width"] + pad)
        y2 = min(h, b["top"] + b["height"] + pad)
        cv2.rectangle(out, (x1, y1), (x2, y2), color, thickness)
    return out


def images_to_pdf(image_paths, out_pdf):
    """בונה PDF שכל עמוד בו הוא תמונה (משוטח, ללא שכבת טקסט)."""
    import fitz
    doc = fitz.open()
    try:
        for p in image_paths:
            pix = fitz.Pixmap(p)
            rect = fitz.Rect(0, 0, pix.width, pix.height)
            page = doc.new_page(width=pix.width, height=pix.height)
            page.insert_image(rect, pixmap=pix)
        doc.save(out_pdf)
    finally:
        doc.close()


# ---- לקוח HTTP ל-Gemma (urllib, ללא תלות חיצונית) ----

def _import_llm_config():
    ref_dir = os.path.join(os.path.dirname(__file__), "..", "references")
    ref_dir = os.path.abspath(ref_dir)
    if ref_dir not in sys.path:
        sys.path.insert(0, ref_dir)
    import llm_config  # noqa: E402
    return llm_config


def list_models():
    """GET /v1/models. מחזיר (ok, info). לשימוש ב-preflight."""
    import urllib.request
    cfg = _import_llm_config()
    url = cfg.BASE_URL.rstrip("/") + "/models"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {cfg.get_api_key()}",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        ids = [m.get("id") for m in data.get("data", [])]
        return True, {"url": url, "models": ids, "target": cfg.MODEL,
                      "target_present": cfg.MODEL in ids}
    except Exception as e:  # noqa: BLE001
        return False, {"url": url, "error": str(e)}


def chat_completion(system_prompt, user_content, json_mode=True):
    """POST /v1/chat/completions. מחזיר את תוכן ההודעה (str)."""
    import urllib.request
    cfg = _import_llm_config()
    url = cfg.BASE_URL.rstrip("/") + "/chat/completions"
    body = {
        "model": cfg.MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {cfg.get_api_key()}",
    })
    with urllib.request.urlopen(req, timeout=cfg.REQUEST_TIMEOUT) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload["choices"][0]["message"]["content"]


def extract_json(text):
    """מנסה לחלץ אובייקט JSON מפלט מודל, כולל תיקון בסיסי אם המודל 'מלכלך'."""
    if text is None:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    # חילוץ בלוק ה-{...} הראשון
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        frag = m.group(0)
        for candidate in (frag, frag.replace("'", '"'), re.sub(r",\s*([}\]])", r"\1", frag)):
            try:
                return json.loads(candidate)
            except Exception:
                continue
    return None
