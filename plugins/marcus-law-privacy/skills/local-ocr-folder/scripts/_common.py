#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_common.py — עזרי-ליבה משותפים לכל סקריפטי ה-OCR.

עיקרון פרטיות: אף פונקציה כאן אינה מחזירה תוכן מסמך. הפונקציות מטפלות
בקבצים, נתיבים, מטא-דאטה ומניפסט בלבד. תוכן ה-OCR נשאר תמיד בקבצים מקומיים.
"""

import os
import re
import sys
import json
import hashlib

import numpy as np

# סיומות שהסקיל מזהה
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
PDF_EXTS = {".pdf"}
SCAN_EXTS = IMAGE_EXTS | PDF_EXTS

# תיקיות פנימיות שאין לסרוק
INTERNAL_DIRS = {"_ocr_out", "_ocr_work"}


def resolve_tesseract():
    """מכוון את pytesseract לבינארי של Tesseract. מכבד את משתנה הסביבה TESSERACT_CMD."""
    import pytesseract
    cmd = os.environ.get("TESSERACT_CMD")
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd
    return pytesseract


def iter_source_files(root):
    """מפיק נתיבים מלאים לכל קובץ מקור בתיקייה, רקורסיבית, תוך דילוג על תיקיות פנימיות."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in INTERNAL_DIRS]
        for fn in sorted(filenames):
            ext = os.path.splitext(fn)[1].lower()
            if ext in SCAN_EXTS:
                yield os.path.join(dirpath, fn)


def doc_key(root, path):
    """מפתח יציב וייחודי למסמך: גזע-שם מנוקה + hash קצר של הנתיב היחסי."""
    rel = os.path.relpath(path, root)
    stem = os.path.splitext(os.path.basename(path))[0]
    safe = re.sub(r"[^\w֐-׿ .()\-]", "_", stem).strip() or "doc"
    h = hashlib.sha1(rel.encode("utf-8")).hexdigest()[:6]
    return f"{safe}__{h}"


def manifest_path(out_dir):
    return os.path.join(out_dir, "manifest.json")


def load_manifest(out_dir):
    p = manifest_path(out_dir)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"root": None, "out_dir": out_dir, "documents": []}


def save_manifest(out_dir, manifest):
    os.makedirs(out_dir, exist_ok=True)
    with open(manifest_path(out_dir), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def find_doc(manifest, key):
    for d in manifest.get("documents", []):
        if d.get("key") == key:
            return d
    return None


# ---- קלט/פלט תמונה שעובד עם נתיבים בעברית ב-Windows ----

def imread_unicode(path, flags=None):
    """cv2.imread שעובד עם נתיבי Unicode (עברית) ב-Windows."""
    import cv2
    if flags is None:
        flags = cv2.IMREAD_COLOR
    data = np.fromfile(path, dtype=np.uint8)
    if data.size == 0:
        return None
    return cv2.imdecode(data, flags)


def imwrite_unicode(path, img, ext=".png"):
    """cv2.imwrite שעובד עם נתיבי Unicode (עברית) ב-Windows."""
    import cv2
    ok, buf = cv2.imencode(ext, img)
    if not ok:
        raise IOError(f"encode failed for {path}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    buf.tofile(path)
    return True


def eprint(*args, **kwargs):
    """הדפסה ל-stderr (לוגים תפעוליים), כדי לא לזהם את פלט המטא-דאטה ב-stdout."""
    print(*args, file=sys.stderr, **kwargs)
