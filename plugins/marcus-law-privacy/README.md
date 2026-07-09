# marcus-law-privacy

חבילת פרטיות לעיבוד מסמכי לקוחות **מקומית**, לפני שמעבירים אותם לניתוח במודל שפה חיצוני.

## עיקרון-העל (הקו האדום)

קו ברזל אחד עומד בבסיס החבילה:

> **המודל (Claude) רק מתזמר את התהליך ולעולם לא קורא את תוכן ה-OCR או ה-PDF הגולמי לתוך חלון ההקשר שלו.**

כל שלב שנוגע בתוכן הוא סקריפט Python דטרמיניסטי שרץ מקומית. הפלט נכתב לקבצים מקומיים בלבד. מה שחוזר למודל הוא אך ורק מטא-דאטה לא-מזהה (מספר עמודים, ציון ביטחון, כמה השחרות בוצעו בכל עמוד) — לעולם לא תוכן.

הרחבה מלאה: `skills/local-ocr-folder/references/privacy-architecture.md`.

## שני הסקיילים

| סקיל | תפקיד | קלט | פלט |
|------|-------|-----|-----|
| **local-ocr-folder** | OCR מקומי של תיקיית מסמכים | תיקייה עם PDF / תמונות | `.txt` נקי, `searchable-PDF`, `.tsv` (תיבות מילים + ביטחון), `manifest.json` |
| **local-redact** | השחרה בלתי-הפיכה מונעת-Gemma | פלט ה-OCR + Gemma מקומי / regex | PDF מושחר משוטח-לתמונה, `.txt` מושחר, `redaction_summary.json` |

הזרימה: **local-ocr-folder ← ואז → local-redact**. ה-TSV שסקיל ה-OCR מפיק הוא הגשר להשחרה — בלי מיקומי המילים אי אפשר לצייר מלבנים שחורים במקום הנכון.

**זיהוי הישויות בהשחרה** נעשה על ידי Gemma מקומי (LM Studio, endpoint תואם-OpenAI ב-LAN); regex + רשימת ישויות הם fallback. הכול מקומי — הבקשה הולכת לרשת הפנימית, לא לענן. הגדרת החיבור: `skills/local-redact/references/llm_config.py`. הטוקן ב-`.env`/משתנה סביבה `LMSTUDIO_API_KEY`, לעולם לא בקוד ולא ב-git.

## התקנה

ראה `skills/local-ocr-folder/INSTALL.md`. בתמצית: Tesseract for Windows (UB Mannheim, עם `heb`) + Python עם החבילות `pymupdf pytesseract pillow opencv-python numpy`.

## הפעלה מהירה

```
# שלב 0 (חד-פעמי) — אימות שהכול מותקן
python scripts/check_deps.py

# שלב 1-4 — OCR מלא על תיקייה (discover → preprocess → ocr → quality)
python scripts/ocr_folder.py "C:\לקוחות\תיק-פלוני"

# השחרה — לפי regex מובנה + רשימת שמות שתספק
python scripts/redact_folder.py "C:\לקוחות\תיק-פלוני\_ocr_out" --names names.txt
```

מה שיודפס למסך ויחזור למודל הוא טבלת סטטוס לא-מזהה בלבד.
