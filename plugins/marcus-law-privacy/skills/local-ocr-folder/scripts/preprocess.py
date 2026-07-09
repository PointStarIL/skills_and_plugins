#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preprocess.py — שלב 2: עיבוד מקדים לכל עמוד (משפר דיוק עברית).

לכל עמוד: רסטור ב-DPI מבוקש -> תיקון כיוון (Tesseract OSD, סיבוב 90/180/270)
-> יישור הטיה (deskew) -> אפור -> בינריזציה (Otsu) -> הסרת רעש.
שומר את תמונות העמודים ל-<out_dir>/<key>/pages/page_XXXX.png.

אינו מוציא תוכן — רק תמונות עמודים ומטא-דאטה של סיבוב.
"""

import os
import sys
import argparse

import numpy as np

from _common import (
    resolve_tesseract, imread_unicode, imwrite_unicode,
    load_manifest, save_manifest, find_doc, PDF_EXTS, eprint,
)


def render_pdf_page(page, dpi):
    """מרנדר עמוד PDF לתמונת OpenCV (BGR) ב-DPI נתון."""
    import fitz
    import cv2
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 1:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    if pix.n == 4:
        return cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)


def correct_orientation(gray):
    """מזהה סיבוב באמצעות Tesseract OSD ומחזיר (gray_rotated, rotation_deg)."""
    import cv2
    pt = resolve_tesseract()
    rotation = 0
    try:
        osd = pt.image_to_osd(gray)
        for line in osd.splitlines():
            if line.startswith("Rotate:"):
                rotation = int(line.split(":")[1].strip())
                break
    except Exception as e:  # noqa: BLE001
        eprint(f"[preprocess] OSD נכשל, ממשיך ללא סיבוב: {e}")
        rotation = 0

    if rotation == 90:
        gray = cv2.rotate(gray, cv2.ROTATE_90_CLOCKWISE)
    elif rotation == 180:
        gray = cv2.rotate(gray, cv2.ROTATE_180)
    elif rotation == 270:
        gray = cv2.rotate(gray, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return gray, rotation


def deskew(gray):
    """יישור הטיה עדינה באמצעות minAreaRect. מיושם רק לזוויות קטנות וסבירות."""
    import cv2
    inv = cv2.bitwise_not(gray)
    thr = cv2.threshold(inv, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thr > 0))
    if coords.shape[0] < 50:
        return gray, 0.0
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = 90 + angle
    # יישור רק להטיות עדינות (מנע over-rotation על עמודים דלילים)
    if abs(angle) < 0.3 or abs(angle) > 15:
        return gray, 0.0
    h, w = gray.shape
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    rotated = cv2.warpAffine(gray, m, (w, h),
                             flags=cv2.INTER_CUBIC,
                             borderMode=cv2.BORDER_REPLICATE)
    return rotated, round(float(angle), 3)


def clean_page(bgr):
    """אפור -> תיקון כיוון -> deskew -> הסרת רעש -> בינריזציה Otsu. מחזיר (binary, meta)."""
    import cv2
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray, rotation = correct_orientation(gray)
    gray, skew = deskew(gray)
    gray = cv2.fastNlMeansDenoising(gray, h=10)
    binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    return binary, {"rotation": rotation, "skew": skew}


def preprocess_document(root, out_dir, doc, dpi=300):
    """מעבד מסמך אחד, שומר תמונות עמודים, ומחזיר רשימת מטא-דאטה לעמודים."""
    src_path = os.path.join(root, doc["rel_path"])
    pages_dir = os.path.join(out_dir, doc["key"], "pages")
    os.makedirs(pages_dir, exist_ok=True)
    ext = doc["ext"].lower()
    page_meta = []

    if ext in PDF_EXTS:
        import fitz
        pdf = fitz.open(src_path)
        try:
            for i, page in enumerate(pdf, 1):
                bgr = render_pdf_page(page, dpi)
                binary, meta = clean_page(bgr)
                out_path = os.path.join(pages_dir, f"page_{i:04d}.png")
                imwrite_unicode(out_path, binary)
                meta.update({"page": i, "width": int(binary.shape[1]),
                             "height": int(binary.shape[0]), "dpi": dpi})
                page_meta.append(meta)
        finally:
            pdf.close()
    else:
        bgr = imread_unicode(src_path)
        if bgr is None:
            raise IOError(f"לא ניתן לקרוא תמונה: {doc['filename']}")
        binary, meta = clean_page(bgr)
        out_path = os.path.join(pages_dir, "page_0001.png")
        imwrite_unicode(out_path, binary)
        meta.update({"page": 1, "width": int(binary.shape[1]),
                     "height": int(binary.shape[0]), "dpi": dpi})
        page_meta.append(meta)

    return page_meta


def main():
    ap = argparse.ArgumentParser(description="עיבוד מקדים של עמודים")
    ap.add_argument("folder", help="נתיב לתיקיית המסמכים (root)")
    ap.add_argument("--out", default=None, help="תיקיית פלט")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--key", default=None, help="עבד רק מסמך בעל key זה")
    args = ap.parse_args()

    root = os.path.abspath(args.folder)
    out_dir = args.out or os.path.join(root, "_ocr_out")
    manifest = load_manifest(out_dir)

    targets = [d for d in manifest["documents"] if d.get("needs_ocr")]
    if args.key:
        targets = [d for d in targets if d["key"] == args.key]

    print(f"עיבוד מקדים ל-{len(targets)} מסמכים ב-DPI {args.dpi}...")
    for d in targets:
        try:
            pm = preprocess_document(root, out_dir, d, dpi=args.dpi)
            d["page_meta"] = pm
            d["preprocessed"] = True
            print(f"  [OK] {d['filename']} — {len(pm)} עמודים")
        except Exception as e:  # noqa: BLE001
            d["preprocessed"] = False
            d["status"] = "failed"
            d["error"] = str(e)
            eprint(f"  [שגיאה] {d['filename']}: {e}")

    save_manifest(out_dir, manifest)


if __name__ == "__main__":
    main()
