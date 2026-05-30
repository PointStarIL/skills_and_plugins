---
name: docx-hebrew-engine
description: >
  התשתית (מקור-אמת יחיד) לייצור מסמכי Word בעברית עם עיצוב אחיד - RTL נכון,
  פונט David, מספור, שוליים וסגנונות בשם. כל סקיל אחר שצריך לייצר או לבנות
  מסמך DOCX בעברית מאפס צריך לפנות לכאן ולהשתמש במנוע `docx_hebrew_engine.py`,
  כדי שכל המסמכים יצאו עם אותו עיצוב וכל שדרוג יחול על כולם.

  הסקיל מספק מנוע python-docx שפותח תבנית קנונית (`references/template.docx`)
  המחזיקה את כל הסגנונות (Normal, List Paragraph עם מספור 1/2/3, Heading 2,
  מספור עברי א/ב/ג), השוליים וה-RTL. הוא מחיל סגנונות בשם ומבטיח RTL נכון
  ברמת ה-run (פתרון מלכודת ה-rtl=0 + bCs לעברית מודגשת).

  טריגרים: "מסמך וורד בעברית", "לבנות docx", "ליצור מסמך מעוצב", "אותו
  עיצוב כמו הטמפלט", "RTL", "פונט David", "מספור עברי א ב ג", או כל בקשה
  לייצר/לבנות מסמך Word בעברית עם הסגנונות הקבועים של המשרד. שאר הסקילים
  (lawmate-cleaner, legal-docx) משתמשים בו כתשתית.
version: "1.0.0"
---

# docx-hebrew-engine - מנוע מסמכי Word בעברית (מקור-אמת יחיד)

סקיל זה הוא **התשתית המשותפת** לייצור מסמכי DOCX בעברית בכל הסקילים. במקום
שכל סקיל יגדיר RTL/פונט/מספור בעצמו, כולם פונים למנוע אחד - כך כל המסמכים
יוצאים עם עיצוב זהה, וכל תיקון או שדרוג (RTL, פונט, מספור, שוליים) חל על
כולם אוטומטית.

## מתי להשתמש

בכל פעם שצריך **לייצר או לבנות מסמך Word בעברית מאפס** עם הסגנונות הקבועים.
אם אתה כותב סקריפט python שמייצר DOCX בעברית - אל תגדיר RTL/פונט/מספור ידנית;
ייבא את `docx_hebrew_engine` והשתמש בפונקציות שלו.

- **lawmate-cleaner** משתמש במנוע לבניית הפלט הנקי.
- **legal-docx** (docx-js, סביבת ענן) - לבנייה מאפס ב-python יש להפנות לכאן;
  ל-tracked changes/comments בעריכת מסמך קיים, ראה את legal-docx.

## מקור-אמת לעיצוב: template.docx

כל הסגנונות, הגדרות המספור, השוליים וה-RTL יושבים ב-`references/template.docx`:

| רכיב | ערך |
|---|---|
| פונט עברי (cs) | David 12pt |
| פונט לטיני (ascii) | Times New Roman |
| יישור גוף | לשני הצדדים, RTL |
| שוליים | top=2.54 ס"מ, bottom=1.9 ס"מ, left=right=3.17 ס"מ |
| `Normal` | סגנון בסיס (RTL, David, מרווח 1.5) |
| `List Paragraph` | גוף ממוספר 1, 2, 3 (numId=14) |
| `Heading 2` | כותרות-משנה |
| numId=43 | מספור עברי א, ב, ג, ד (hebrew1) |
| numId=0 | ביטול מספור (לשורות עם קו תחתון / ללא marker) |

**לשנות עיצוב גלובלית**: פותחים את `references/template.docx` ב-Word, משנים
את הסגנון (Normal / List Paragraph / Heading 2) ושומרים. השינוי חל על כל
המסמכים שייווצרו מעתה, בכל הסקילים. אין צורך לגעת בקוד.

## איך להשתמש במנוע

```python
import sys
from pathlib import Path
# התאם את מספר ה-parents לפי מיקום הסקריפט שלך ביחס לתיקיית הסקילים
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "docx-hebrew-engine" / "scripts"))
import docx_hebrew_engine as hd

doc = hd.open_document()                       # פותח את התבנית
hd.add_heading(doc, "רקע עובדתי")              # Heading 2
hd.add_body(doc, "פסקה ראשונה...")            # List Paragraph, ממוספר 1
hd.add_body(doc, "פסקה שנייה...")             # 2
hd.add_hebrew_item(doc, "סעד מבוקש")          # א.
hd.add_exhibit_ref(doc, "העתק X מצורף ומסומן כנספח 1.")  # קו תחתון, ללא מספר
hd.add_plain(doc, "שורה ללא מספור")           # List Paragraph בלי marker
hd.save(doc, "out.docx")
```

לטקסט שמגיע ממקור חיצוני (AI, הדבקה, law-mate) - להעביר דרך
`hd.sanitize_source_text(t)` כדי להסיר תווי כיווניות נסתרים (LRM/RLM) ולהחליף
מקפים ארוכים (em/en dash) במקף רגיל.

הדגשה inline: עוטפים מקטע ב-`hd.BOLD_OPEN`..`hd.BOLD_CLOSE` בתוך הטקסט, ו-
`add_body`/`add_formatted_text` יהפכו אותו ל-run מודגש (כולל bCs לעברית).

## ה-API

| פונקציה | תפקיד |
|---|---|
| `open_document()` | פותח את התבנית, מסיר placeholder, מחזיר `Document` |
| `add_heading(doc, text)` | כותרת-משנה (Heading 2) |
| `add_body(doc, text)` | פסקת גוף ממוספרת 1, 2, 3 |
| `add_hebrew_item(doc, text)` | פסקה ממוספרת א, ב, ג (hebrew1) |
| `add_exhibit_ref(doc, text)` | שורה עם קו תחתון, ללא marker |
| `add_plain(doc, text)` | פסקת גוף ללא מספור |
| `add_run(p, text, bold, underline)` | run בודד עם RTL (פרימיטיב) |
| `add_formatted_text(p, text, underline)` | טקסט עם הדגשות inline |
| `set_numbering(p, num_id, ilvl=0)` | החלת numPr מפורש |
| `sanitize_source_text(t)` | ניקוי LRM/RLM + מקפים ארוכים |
| `save(doc, path)` | שמירה |

## העיקרון הקריטי: RTL ברמת ה-run

סגנון `List Paragraph` בתבנית נושא `<w:rtl w:val="0"/>` שמכבה RTL. לכן **כל
run מקבל `<w:rtl/>` מפורש** שדורס זאת - אחרת Word מתייחס לעברית כ-LTR ומציג
אותה בפונט ה-ascii (Times New Roman) במקום David, מיושר שמאלה. שמות מודגשים
מקבלים גם `<w:bCs/>` (bold complex-script - עברית מתבלטת רק כך). **אין** לקבוע
`rFonts`/`sz` ברמת ה-run; הם מגיעים מהסגנון. `add_run` עושה את כל זה.

## הוספת יכולות חדשות

כל יכולת עיצוב/בנייה חדשה צריכה להתווסף **כאן** (ולא בסקילים הצרכנים), כדי
שתהיה זמינה לכולם. דוגמאות עתידיות: טבלאות RTL, הערות שוליים, חתימות.
