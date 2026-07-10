# CHANGELOG — local-redact

## 0.2.2
- טוקן לכל הפרויקטים: `_load_dotenv` קורא כעת גם קובץ גלובלי קבוע `~/.lmstudio.env` (בבית המשתמש) — נקרא מכל תיקיית עבודה, ללא תלות ב-cwd או בעומק הפרויקט. עדיפות: env var > `.env` של הפרויקט > `~/.lmstudio.env`. תועד ב-README.

## 0.2.1
תיקוני תקלות שגרמו לנפילה שקטה ל-regex ולהשארת שמות/כתובות לקוח חשופים (אומתו 2026-07-10):
- **טוקן:** `get_api_key()` נקרא רק מ-`.env`/env-var (לא מ-`.env.example`), והשרת אוכף טוקן (401 בלי טוקן) → נפילה ל-regex. תועד ב-README (משתנה סביבה + `.env`) ונוקה טוקן שדלף ל-`.env.example`.
- **response_format:** השרת דוחה `json_object` (400) → `chat_completion` עבר ל-`json_schema` עם סכימה מפורשת (`ENTITIES_SCHEMA`).
- **מיפוי שמות RTL:** `find_entity_boxes` לא מצא שמות רב-מיליים בעברית (מילים ממוינות LTR מול קריאה RTL) → השוואה לשני סדרי המילים.
- **גודל PDF:** `images_to_pdf` הטמיע pixmap גולמי (~59MB) → JPEG q80 + הקטנה ל-~2400px (~1.5MB).
- **דיוק:** prompt הזיהוי צומצם ל"לקוח/עורר בלבד" (לא חברי ועדה/רופאים/תאריכים/סכומים/מספרי תיק/טלפונים ציבוריים).

## 0.2.0
- זיהוי ישויות עבר ל-Gemma מקומי (LM Studio, endpoint תואם-OpenAI ב-LAN).
- שכבת קונפיג משותפת references/llm_config.py + טעינת .env (טוקן לא בקוד).
- preflight_gemma.py, detect_entities.py, map_boxes.py, review.py, burn_redactions.py.
- שער אנושי: הצריבה נפרדת (--burn) אחרי preview.
- Fallback ל-regex + רשימת ישויות (--engine gemma|regex|both).

## 0.1.0
- גרסה ראשונה מבוססת regex + רשימת ישויות (הפכה ל-fallback).
