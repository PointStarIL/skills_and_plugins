---
name: local-redact
description: "משחיר מקומית פרטים מזהים במסמכי לקוח לקראת ניתוח במודל שפה חיצוני. זיהוי הישויות נעשה על ידי Gemma מקומי (LM Studio, endpoint תואם-OpenAI ב-LAN) שקורא את הטקסט ומזהה לבד שמות/ת\"ז/טלפונים/כתובות/מספרי תיק; regex + רשימת ישויות משמשים כ-fallback (--engine gemma|regex|both). הכול מקומי — הבקשה הולכת לרשת הפנימית ולא לענן. Human Gate חובה לפני צריבה. הפלט הוא PDF מושחר משוטח-לתמונה (בלתי-הפיך). המתזמר מקבל בחזרה רק סטטיסטיקה לא-מזהה, לעולם לא תוכן או ערכים. הפעל כאשר: 'השחר מסמך', 'הסתר פרטים מזהים', 'redact', 'local redact'. דורש קודם הרצת local-ocr-folder."
metadata:
  version: "1.0.0"
---

# local-redact, השחרה מקומית מונעת-Gemma

סקיל זה מזהה פרטים רגישים בעזרת **Gemma מקומי** (או regex כ-fallback), ממפה אותם חזרה למיקומים לפי ה-TSV של ה-OCR, מעביר דרך **שער אישור אנושי**, וצורב השחרה בלתי-הפיכה. **המתזמר (Claude) לא נמצא באף שלב שנוגע בתוכן** — הסקריפט מדבר ישירות עם Gemma ומחזיר לי רק ספירות.

## עיקרון-העל — חובה

ראה `references/privacy-architecture.md`. בתמצית:

- **הסקריפט מדבר עם Gemma; אני (המודל המתזמר) לא קורא את תוכן המסמך ולא את פלט Gemma לתוך ההקשר שלי.** אחרת התוכן עולה לענן.
- Gemma רץ על הרשת הפנימית (LAN) — הבקשה לא יוצאת החוצה.
- **אל תקרא לעולם**: `words.tsv`, `text.txt`, `entities.json`, `redaction_plan.json`, `review_preview.pdf`, `redacted.pdf`, `redacted.txt`. אלה קבצים מקומיים רגישים.
- מותר לקרוא: `redaction_summary.json` בלבד (ספירות לפי קטגוריה ועמוד — ללא ערכים).
- הטוקן לעולם לא בקוד — רק במשתנה סביבה `LMSTUDIO_API_KEY` או בקובץ `.env` מקומי שאינו נכנס ל-git.

## דרישות מוקדמות

1. הרצת `local-ocr-folder` על התיקייה → קיימת `_ocr_out` עם `words.tsv` ותמונות עמודים לכל מסמך.
2. שרת Gemma פעיל (LM Studio) — ברירת מחדל `http://192.168.10.216:1234/v1`, מודל `google/gemma-4-e4b`. ראה `references/llm_config.py`.
3. הגדרת הטוקן: `set LMSTUDIO_API_KEY=...` או קובץ `.env` בתיקיית הפרויקט.

תמיד הרץ preflight תחילה:

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/local-redact/scripts/preflight_gemma.py"
```

אם השרת כבוי — הוא נעצר עם הודעה ברורה. אפשר להמשיך עם `--engine regex` (בלי Gemma).

## הרצה — המסלול המהיר

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/local-redact/scripts/redact_folder.py" "<נתיב ל-_ocr_out>"
```

ברירת המחדל: `--engine both` (Gemma + regex, איחוד), מריץ עד שלב ה-preview **ולא צורב**. הצריבה היא פקודה נפרדת (שער אנושי).

דגלים:

- `--engine gemma|regex|both` — מנוע זיהוי. `gemma` נופל אוטומטית ל-`regex` אם השרת לא זמין. ברירת מחדל `both`.
- `--names names.txt` — מונחים לכפיית השחרה (שם/כתובת/מספר תיק בכל שורה).
- `--allowlist allow.txt` — מונחים שלעולם לא יושחרו.
- `--burn` — בצע גם את הצריבה הבלתי-הפיכה (רק אחרי שסקרת את ה-preview).
- `--pad 2` — ריפוד פיקסלים סביב כל מלבן.

## מסלול הנתונים (חוק הברזל נשמר)

```
TSV + תמונות עמודים (מ-OCR)
  → detect_entities.py  שולח טקסט עמוד-עמוד ל-Gemma (LAN) → entities.json (מקומי, רגיש)
  → map_boxes.py        ממפה כל ישות למילים ב-TSV (סובלנות OCR + RTL) → redaction_plan.json
  → review.py           preview PDF עם מלבנים שקופים + טבלת "מה יושחר ולמה"  ← שער אנושי
  → burn_redactions.py  צביעת פיקסלים בשחור + שיטוח לתמונה → <שם>.redacted.pdf (בלתי-הפיך)
```

בכל השלבים המתזמר מקבל רק `redaction_summary.json` (ספירות).

## פירוט השלבים

1. **preflight_gemma.py** — בודק `GET /v1/models`. עוצר בבירור אם השרת כבוי או הפורט חסום.
2. **detect_entities.py** — לכל עמוד קורא ל-endpoint התואם-OpenAI (`temperature: 0`, `response_format: json_object`), מבקש `{"entities":[{"text","type"}]}`. כולל תיקון JSON + retry אם המודל הקטן מחזיר פלט לא תקין. שולח עמוד-עמוד (חלון הקשר מוגבל + מיפוי לעמוד הנכון). כותב `entities.json` (מקומי).
3. **map_boxes.py** — מתאים כל מחרוזת ישות למילים ב-TSV עם סובלנות לשגיאות OCR (רווחים/`\s` בין מילים, נו"ן/מ"ם סופית, גרש חסר) וטיפול RTL/bidi. במנוע `regex`/`both` מוסיף גם התאמות regex מובנות. מפיק `redaction_plan.json`.
4. **review.py** — שער אנושי: מפיק `review_preview.pdf` עם המלבנים המוצעים בשקיפות (עדיין לא צרובים) וטבלת "מה יושחר ולמה". אתה פותח מקומית, מאשר/מוריד/מוסיף (עריכת `redaction_plan.json` או `names`/`allowlist` והרצה חוזרת).
5. **burn_redactions.py** — מרסטר, צובע פיקסלים בשחור, שומר מחדש כתמונה. אין שכבת טקסט מתחת → בלתי-הפיך. פלט: `<שם-קובץ>.redacted.pdf`.

## נפילה לאחור (Fallback)

אם Gemma לא זמין, הסקריפט חוזר אוטומטית ל-regex + רשימת ישויות. כך ההשחרה לעולם אינה תלויה לגמרי בשרת. תיעוד ה-regex: `references/redaction-patterns.md`.

## דיווח ואימות אנושי

קרא `redaction_summary.json` והצג טבלה: כמה ישויות בכל קטגוריה/מסמך/עמוד, ואיזה מנוע רץ. **הדגש**: הצריבה בלתי-הפיכה; האחריות לאמת ויזואלית שכל פרט כוסה היא של המשתמש — שיפתח את `review_preview.pdf` מקומית לפני `--burn`.

## תלויות

- **Python**: `pymupdf`, `pillow`, `opencv-python`, `numpy` (כבר מותקנים עבור local-ocr-folder). קריאות ה-LLM דרך `urllib` בלבד (ללא חבילה נוספת).
- **שרת Gemma** תואם-OpenAI ב-LAN (LM Studio). לא נדרש Tesseract.
