#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_deps.py — שלב 0: אימות תלויות, בלי לגעת בשום מסמך.

בודק חבילות Python, את הבינארי של Tesseract, ואת חבילות השפה (heb/eng/heb_old).
מדפיס טבלה קריאה + סיכום JSON. יוצא עם קוד 0 אם כל הדרוש קיים, אחרת 1.
"""

import sys
import json

REQUIRED_PACKAGES = [
    ("fitz", "pymupdf"),
    ("pytesseract", "pytesseract"),
    ("PIL", "pillow"),
    ("cv2", "opencv-python"),
    ("numpy", "numpy"),
]

REQUIRED_LANGS = ["heb", "eng"]
OPTIONAL_LANGS = ["heb_old"]


def check_package(mod_name, pip_name):
    try:
        __import__(mod_name)
        return True, ""
    except Exception as e:  # noqa: BLE001
        return False, f"pip install {pip_name}"


def main():
    report = {"packages": {}, "tesseract": {}, "languages": {}, "ok": True}
    lines = []
    lines.append("== בדיקת חבילות Python ==")

    for mod_name, pip_name in REQUIRED_PACKAGES:
        ok, hint = check_package(mod_name, pip_name)
        report["packages"][pip_name] = ok
        lines.append(f"  [{'OK ' if ok else 'חסר'}] {pip_name}" + ("" if ok else f"  ->  {hint}"))
        if not ok:
            report["ok"] = False

    lines.append("")
    lines.append("== בדיקת Tesseract ==")

    tess_ok = False
    langs = []
    try:
        import pytesseract
        import os
        cmd = os.environ.get("TESSERACT_CMD")
        if cmd:
            pytesseract.pytesseract.tesseract_cmd = cmd
        version = str(pytesseract.get_tesseract_version())
        report["tesseract"]["version"] = version
        report["tesseract"]["found"] = True
        tess_ok = True
        lines.append(f"  [OK ] Tesseract גרסה {version}")
        try:
            langs = list(pytesseract.get_languages(config=""))
        except Exception:
            langs = []
    except Exception as e:  # noqa: BLE001
        report["tesseract"]["found"] = False
        report["tesseract"]["error"] = str(e)
        report["ok"] = False
        lines.append("  [חסר] Tesseract לא נמצא. ראה INSTALL.md.")
        lines.append("        אם מותקן אך לא ב-PATH, הגדר: set TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe")

    lines.append("")
    lines.append("== חבילות שפה ==")
    if tess_ok:
        for lg in REQUIRED_LANGS:
            present = lg in langs
            report["languages"][lg] = present
            lines.append(f"  [{'OK ' if present else 'חסר'}] {lg} (נדרש)")
            if not present:
                report["ok"] = False
        for lg in OPTIONAL_LANGS:
            present = lg in langs
            report["languages"][lg] = present
            lines.append(f"  [{'OK ' if present else '--'}] {lg} (אופציונלי)")
    else:
        lines.append("  (דילוג — Tesseract לא נמצא)")

    lines.append("")
    lines.append("=" * 40)
    lines.append("תוצאה: " + ("OK — הכול מוכן." if report["ok"] else "חסרים רכיבים. ראה INSTALL.md."))

    print("\n".join(lines))
    print("\n--- JSON ---")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    sys.exit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
