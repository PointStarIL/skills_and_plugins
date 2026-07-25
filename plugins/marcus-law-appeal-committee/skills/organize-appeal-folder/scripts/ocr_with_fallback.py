#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR עם נפילה אוטומטית ל-Mistral OCR API.

זרימה:
1. מריץ OCR מקומי עם Tesseract (עברית + אנגלית) על כל עמודי ה-PDF.
2. מחשב ציון איכות (ביטחון ממוצע, כמות טקסט, יחס תווים תקינים).
3. אם האיכות מתחת לסף שנקבע, מבצע OCR מחדש דרך Mistral OCR API.

שימוש:
    from ocr_with_fallback import ocr_pdf
    result = ocr_pdf("file.pdf")
    print(result["text"])          # הטקסט הסופי
    print(result["engine_used"])   # 'tesseract' או 'mistral'

או משורת הפקודה:
    python3 ocr_with_fallback.py file.pdf [--out out.txt] [--force-mistral] [--page-markers]

--page-markers מוסיף שורת "===== PAGE n =====" לפני כל עמוד. מומלץ תמיד:
זה מה ש-export_ocr_text.py קורא כדי לבנות קובצי md עם סימון עמודים, וזה מה
שמאפשר לחתוך טווח עמודים של נספח מתוך פלט של קובץ גדול.

דרוש מפתח API:  משתנה סביבה  MISTRAL_API_KEY
"""

import os
import re
import sys
import json
import base64
import argparse

import pytesseract
from pdf2image import convert_from_path
import requests

# ---------- הגדרות ניתנות לכוונון ----------
# שם המודל: תומך גם בשם המשתנה של Infisical (OCR_MODEL) וגם ב-MISTRAL_OCR_MODEL
MISTRAL_MODEL = (
    os.environ.get("MISTRAL_OCR_MODEL")
    or os.environ.get("OCR_MODEL")
    or "mistral-ocr-latest"
)
MISTRAL_ENDPOINT = "https://api.mistral.ai/v1/ocr"
OCR_DPI = 300
TESS_LANG = "heb+eng"

# ספי איכות: אם *אחד* מהם נופל מתחת לסף, מפעילים את Mistral
MIN_MEAN_CONFIDENCE = 60.0   # ביטחון ממוצע של Tesseract (0-100)
MIN_CHARS_PER_PAGE = 80      # מינימום תווים לעמוד (עמוד עם מעט טקסט חשוד)
MIN_VALID_CHAR_RATIO = 0.75  # יחס מינימלי של תווים "תקינים" (עברית/לטינית/ספרות/פיסוק)

# סמן עמוד; export_ocr_text.py מסתמך על הפורמט הזה
PAGE_MARKER = "\n\n===== PAGE {n} =====\n"
# -------------------------------------------

# תווים נחשבים תקינים: עברית, לטינית, ספרות, רווח, פיסוק נפוץ, ניקוד
_VALID_CHARS = re.compile(
    r"[֐-׿A-Za-z0-9\s\.\,\;\:\!\?\(\)\[\]\{\}\-\–\"'\/\\%&@#\*\+=°₪$]"
)


def _valid_char_ratio(text: str) -> float:
    stripped = text.strip()
    if not stripped:
        return 0.0
    valid = len(_VALID_CHARS.findall(stripped))
    return valid / len(stripped)


def tesseract_ocr(pdf_path: str, dpi: int = OCR_DPI, lang: str = TESS_LANG):
    """מריץ Tesseract על כל עמוד ומחזיר טקסט + מדדי איכות."""
    images = convert_from_path(pdf_path, dpi=dpi)
    pages_text = []
    confidences = []

    for img in images:
        # טקסט העמוד
        page_text = pytesseract.image_to_string(img, lang=lang)
        pages_text.append(page_text)

        # ביטחון ברמת המילה
        data = pytesseract.image_to_data(
            img, lang=lang, output_type=pytesseract.Output.DICT
        )
        for conf, word in zip(data["conf"], data["text"]):
            try:
                c = float(conf)
            except (ValueError, TypeError):
                continue
            if c >= 0 and word.strip():
                confidences.append(c)

    full_text = "\n\n".join(pages_text)
    mean_conf = sum(confidences) / len(confidences) if confidences else 0.0
    n_pages = max(len(images), 1)

    metrics = {
        "mean_confidence": round(mean_conf, 1),
        "chars_per_page": round(len(full_text.strip()) / n_pages, 1),
        "valid_char_ratio": round(_valid_char_ratio(full_text), 3),
        "num_pages": n_pages,
        "total_chars": len(full_text.strip()),
    }
    return full_text, metrics, pages_text


def assess_quality(metrics: dict):
    """מחזיר (ok: bool, reasons: list) — האם ה-OCR המקומי מספיק טוב."""
    reasons = []
    if metrics["mean_confidence"] < MIN_MEAN_CONFIDENCE:
        reasons.append(
            f"ביטחון ממוצע נמוך ({metrics['mean_confidence']} < {MIN_MEAN_CONFIDENCE})"
        )
    if metrics["chars_per_page"] < MIN_CHARS_PER_PAGE:
        reasons.append(
            f"מעט טקסט לעמוד ({metrics['chars_per_page']} < {MIN_CHARS_PER_PAGE})"
        )
    if metrics["valid_char_ratio"] < MIN_VALID_CHAR_RATIO:
        reasons.append(
            f"יחס תווים תקינים נמוך ({metrics['valid_char_ratio']} < {MIN_VALID_CHAR_RATIO})"
        )
    return (len(reasons) == 0), reasons


def mistral_ocr(pdf_path: str, model: str = MISTRAL_MODEL):
    """מבצע OCR דרך Mistral OCR API ומחזיר טקסט (Markdown)."""
    # מפתח ה-API: תומך גם בשם המשתנה של Infisical (API_KEY) וגם ב-MISTRAL_API_KEY
    api_key = os.environ.get("MISTRAL_API_KEY") or os.environ.get("API_KEY")
    if not api_key:
        raise RuntimeError("חסר משתנה סביבה MISTRAL_API_KEY / API_KEY")

    with open(pdf_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "model": model,
        "document": {
            "type": "document_url",
            "document_url": f"data:application/pdf;base64,{b64}",
        },
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    resp = requests.post(MISTRAL_ENDPOINT, headers=headers, json=payload, timeout=300)
    resp.raise_for_status()
    data = resp.json()

    pages = data.get("pages", [])
    pages_text = [p.get("markdown", "") for p in pages]
    text = "\n\n".join(pages_text)
    return text, data, pages_text


def ocr_pdf(pdf_path: str, force_mistral: bool = False, verbose: bool = True):
    """
    פונקציה ראשית: מריצה OCR מקומי, בודקת איכות, ונופלת ל-Mistral בעת הצורך.
    מחזירה dict עם: text, engine_used, tesseract_metrics, fallback_reasons.
    """
    result = {
        "text": "",
        "pages": [],
        "engine_used": None,
        "tesseract_metrics": None,
        "fallback_reasons": [],
    }

    if force_mistral:
        text, _, pages = mistral_ocr(pdf_path)
        result.update(text=text, pages=pages, engine_used="mistral",
                      fallback_reasons=["הופעל ידנית (force_mistral)"])
        return result

    # שלב 1 – OCR מקומי
    tess_text, metrics, tess_pages = tesseract_ocr(pdf_path)
    result["tesseract_metrics"] = metrics
    ok, reasons = assess_quality(metrics)

    if verbose:
        print(f"[Tesseract] מדדים: {metrics}", file=sys.stderr)

    if ok:
        result.update(text=tess_text, pages=tess_pages, engine_used="tesseract")
        if verbose:
            print("[OK] ה-OCR המקומי תקין — לא נדרשת נפילה ל-Mistral", file=sys.stderr)
        return result

    # שלב 2 – נפילה ל-Mistral
    result["fallback_reasons"] = reasons
    if verbose:
        print(f"[Fallback] נופל ל-Mistral בגלל: {'; '.join(reasons)}", file=sys.stderr)
    try:
        mistral_text, _, mistral_pages = mistral_ocr(pdf_path)
        result.update(text=mistral_text, pages=mistral_pages, engine_used="mistral")
    except Exception as e:
        # אם Mistral נכשל, מחזירים את התוצאה המקומית עם אזהרה
        if verbose:
            print(f"[שגיאה] Mistral נכשל ({e}) — מחזיר תוצאת Tesseract", file=sys.stderr)
        result.update(text=tess_text, pages=tess_pages, engine_used="tesseract",
                      fallback_reasons=reasons + [f"Mistral נכשל: {e}"])
    return result


def main():
    ap = argparse.ArgumentParser(description="OCR עם נפילה ל-Mistral OCR")
    ap.add_argument("pdf", help="נתיב לקובץ PDF")
    ap.add_argument("--out", help="קובץ פלט לטקסט (ברירת מחדל: stdout)")
    ap.add_argument("--force-mistral", action="store_true",
                    help="דלג על OCR מקומי ולך ישר ל-Mistral")
    ap.add_argument("--page-markers", action="store_true",
                    help="הוסף '===== PAGE n =====' לפני כל עמוד (נדרש ל-export_ocr_text.py)")
    args = ap.parse_args()

    res = ocr_pdf(args.pdf, force_mistral=args.force_mistral)

    out_text = res["text"]
    if args.page_markers and res["pages"]:
        out_text = "".join(PAGE_MARKER.format(n=i) + p
                           for i, p in enumerate(res["pages"], 1))

    print(f"\n=== מנוע: {res['engine_used']} ===", file=sys.stderr)
    if res["fallback_reasons"]:
        print(f"=== סיבות נפילה: {res['fallback_reasons']} ===", file=sys.stderr)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out_text)
        print(f"נשמר: {args.out} ({len(res['pages'])} עמודים)", file=sys.stderr)
    else:
        print(out_text)


if __name__ == "__main__":
    main()
