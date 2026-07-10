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
            # התאמת רצף מילים סמוכות (שם מלא / כתובת / מספר מפוצל).
            # עברית נקראת ימין->שמאל אך המילים ממוינות לפי left עולה, לכן רצף
            # רב-מילים מופיע במערך בסדר הפוך. משווים את היעד לשני הסדרים.
            matched = False
            for j in range(i, min(i + 8, n)):
                seg = norms[i:j + 1]
                acc = "".join(seg)
                acc_rev = "".join(reversed(seg))
                if len(acc) < len(target) * 0.6:
                    continue
                if (acc == target or acc_rev == target
                        or similar(acc, target) >= threshold
                        or similar(acc_rev, target) >= threshold):
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


def images_to_pdf(image_paths, out_pdf, jpeg_quality=80, max_long_side=2400):
    """בונה PDF שכל עמוד בו הוא תמונה מכווצת (JPEG), משוטח, ללא שכבת טקסט.

    ממיר כל עמוד ל-JPEG ומקטין רזולוציה כדי לשמור על גודל קובץ סביר —
    הטמעת pixmap גולמי מנפחת את ה-PDF (עמוד 300DPI גולמי ~8-9MB). JPEG
    באיכות 80 ורוחב מרבי ~2400px (~200DPI ל-A4) שומר על קריאוּת ומקטין פי עשרות.
    """
    import fitz
    import cv2
    doc = fitz.open()
    try:
        for p in image_paths:
            img = imread_unicode(p, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            h, w = img.shape[:2]
            long_side = max(h, w)
            if max_long_side and long_side > max_long_side:
                scale = max_long_side / float(long_side)
                img = cv2.resize(img, (max(1, int(w * scale)), max(1, int(h * scale))),
                                 interpolation=cv2.INTER_AREA)
                h, w = img.shape[:2]
            ok, buf = cv2.imencode(".jpg", img,
                                   [cv2.IMWRITE_JPEG_QUALITY, int(jpeg_quality)])
            if not ok:
                continue
            rect = fitz.Rect(0, 0, w, h)
            page = doc.new_page(width=w, height=h)
            page.insert_image(rect, stream=buf.tobytes())
        doc.save(out_pdf, garbage=4, deflate=True)
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


def chat_completion(system_prompt, user_content, json_mode=True, schema=None):
    """POST /v1/chat/completions. מחזיר את תוכן ההודעה (str).

    schema: אם ניתן, נאכף פלט JSON תואם-סכימה (response_format=json_schema).
    הערה: שרתי LM Studio מקבלים 'json_schema' או 'text' בלבד — לא 'json_object'.
    """
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
    if schema is not None:
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "structured_output", "strict": True, "schema": schema},
        }
    elif json_mode:
        body["response_format"] = {"type": "text"}
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
