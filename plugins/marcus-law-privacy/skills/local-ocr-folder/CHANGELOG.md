# CHANGELOG — local-ocr-folder

## 0.1.0
- גרסה ראשונה. שרשרת OCR מקומית מלאה: check_deps, discover, preprocess, run_ocr, quality_report, ו-entrypoint ocr_folder.
- מנוע רסטור: PyMuPDF (ללא Poppler).
- שפות ברירת מחדל: heb+eng. תמיכה אופציונלית ב-heb_old.
- פלט לכל מסמך: TXT נקי, searchable-PDF, ו-TSV (תיבות מילים + ביטחון).
- כל הפלט מקומי; ה-stdout ומניפסט מכילים מטא-דאטה בלבד.
