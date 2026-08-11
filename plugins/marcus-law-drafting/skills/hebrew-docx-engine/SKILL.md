---
name: hebrew-docx-engine
description: "התשתית (מקור-אמת יחיד) לייצור מסמכי Word בעברית עם עיצוב אחיד: RTL נכון, פונט David, מספור בארבע רמות, שוליים וסגנונות בשם, דרך המנוע docx_hebrew_engine.py ותבנית references/template.docx. כל סקיל שבונה DOCX עברי מאפס חייב לעבור דרכו, כך שכל המסמכים אחידים וכל שדרוג עיצוב חל על כולם. הפעל כאשר: 'מסמך וורד בעברית', 'לבנות docx בעברית', 'אותו עיצוב כמו הטמפלט', 'פונט David', 'מספור עברי א ב ג', או כתיבת סקריפט שמייצר DOCX עברי. למבנה/תוכן מסמכים משפטיים ולעריכה מתקדמת ראה edit-legal-docx."
metadata:
  version: "1.0.0"
---

# hebrew-docx-engine - מנוע מסמכי Word בעברית (מקור-אמת יחיד)

**במערכת הזו יש מנוע DOCX אחד בלבד, והוא כאן.** במקום שכל סקיל יגדיר RTL, פונט
ומספור בעצמו, כולם פונים למנוע הזה, ולכן כל המסמכים יוצאים עם עיצוב זהה וכל
תיקון או שדרוג חל על כולם אוטומטית.

**מיקום:** `plugins/marcus-law-drafting/skills/hebrew-docx-engine/`
`scripts/docx_hebrew_engine.py` (המנוע) + `references/template.docx` (העיצוב).

## מתי להשתמש

בכל בנייה של מסמך Word בעברית **מאפס**. אם אתה כותב סקריפט python שמייצר DOCX
עברי - אל תגדיר RTL, פונט או מספור ידנית, וייבא את המנוע.

- **edit-legal-docx**, **organize-client-folder**, **extract-appeal-claims** ו-**write-appeal-decision**
  בונים דרכו. **אין במערכת מנוע DOCX שני, ואין חריגים.**
- **edit-legal-docx** מטפל בעריכת DOCX **קיים** (tracked changes, comments) ובמבנה
  המשפטי של סוגי מסמכים; לבנייה מאפס הוא מפנה לכאן.

## מקור-אמת לעיצוב: template.docx

כל הסגנונות, המספור, השוליים וה-RTL יושבים ב-`references/template.docx` (61 סגנונות):

| רכיב | ערך |
|---|---|
| פונט עברי (cs) | David 12pt (`szCs=24`) |
| פונט לטיני (ascii) | Times New Roman 10pt (`sz=20`) |
| `w:bidi` + `w:rtlGutter` ב-sectPr | הסקשן עצמו RTL |
| כותרת תחתונה | "עמוד X מתוך Y", ממורכזת |
| `Normal` | סגנון בסיס, יישור לשני הצדדים (`jc=both`) |
| `Title` | כותרת ראשית של המסמך |
| `סעיף` | פסקת גוף ממוספרת, ארבע רמות (numId=5) |
| `Heading 2` | כותרת-משנה |
| `Heading 3` | כותרת משנה-משנה |
| `Quote` | ציטוטים |
| `Subtitle` | שורת נספח |

### ארבע רמות המספור של סגנון "סעיף" (numId=5)

| level | פורמט | הסימן |
|---|---|---|
| 0 | decimal | `1.` |
| 1 | hebrew1 | `א.` |
| 2 | decimal | `(1)` |
| 3 | hebrew2 | `(א)` |

**לשנות עיצוב גלובלית**: פותחים את `references/template.docx` ב-Word, משנים את
הסגנון ושומרים. השינוי חל על כל המסמכים שייווצרו מעתה בכל הסקילים, בלי לגעת בקוד.

## איך להשתמש במנוע

```python
import sys
from pathlib import Path
# התאם את מספר ה-parents לפי מיקום הסקריפט ביחס לתיקיית הסקילים
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hebrew-docx-engine" / "scripts"))
import docx_hebrew_engine as hd

doc = hd.open_document()                        # פותח את התבנית
hd.add_heading(doc, "רקע עובדתי")               # Heading 2
hd.add_clause(doc, "פסקה ראשונה...")            # סעיף, רמה 0 -> 1.
hd.add_clause(doc, "תת-סעיף...", level=1)       # רמה 1 -> א.
hd.add_heading3(doc, "כותרת משנה")              # Heading 3
hd.add_quote(doc, "ציטוט מפסק דין")             # Quote
hd.add_exhibit_ref(doc, "העתק X מצורף ומסומן כנספח 1.")   # Subtitle
hd.add_plain(doc, "פסקה ללא מספור")             # Normal
hd.save(doc, "out.docx")
```

**ניקוי טקסט אוטומטי.** `add_run` מריץ `sanitize_source_text` על כל טקסט שנכנס למסמך,
ולכן תווי כיווניות נסתרים (LRM/RLM) ומקפים ארוכים או בינוניים (em/en dash) מוסרים
אוטומטית. זו נקודת המעבר היחידה של טקסט למסמך, ולכן ההגנה חלה על כל הפונקציות: פסקאות,
כותרות, ציטוטים ותאי טבלה. אפשר לקרוא ל-`hd.sanitize_source_text(t)` גם ישירות, כשצריך
לנקות מחרוזת לפני שימוש אחר.

זו רשת ביטחון למסמכים ולא תחליף לכלל הכתיבה: היא אינה מגיעה לפלט למסך או ל-Markdown.

**פורמט תאריכים.** תאריכים שנכתבים לתוך מסמך הם `יום.חודש.שנה`, **ללא אפסים מובילים**,
עם שנה בת שתי ספרות: `11.8.26`, `1.1.26`, `25.12.26`, `8.5.26`. לא `08.05.26` ולא
`08.05.2026`. זה כלל כתיבה שחל על הטקסט שאתה מעביר למנוע, והמנוע אינו אוכף אותו.

הדגשה inline: עוטפים מקטע ב-`hd.BOLD_OPEN`..`hd.BOLD_CLOSE` בתוך הטקסט.

טבלת RTL: `add_table` מייצרת טבלה שהעמודות בה זורמות מימין לשמאל (העמודה
הראשונה בימין) וכל תא הוא RTL. ב-`widths` (ס"מ) האיבר הראשון הוא העמודה הימנית.

```python
hd.add_table(
    doc,
    headers=["#", "שם המסמך", "תאריך", "תיאור"],
    rows=[["1", "כתב ערר", "25.03.26", "טענות העוררים..."]],
    widths=[0.8, 4.6, 1.6, 7.6],   # מימין לשמאל
)
```

## ה-API

| פונקציה | תפקיד |
|---|---|
| `open_document()` | פותח את התבנית, מסיר placeholder, מחזיר `Document` |
| `add_title(doc, text)` | כותרת ראשית של המסמך (Title) |
| `add_clause(doc, text, level=0)` | פסקת `סעיף` ברמה 0 עד 3 (עם ולידציה) |
| `add_body(doc, text)` | עטיפה של `add_clause(level=0)` |
| `add_hebrew_item(doc, text)` | עטיפה של `add_clause(level=1)` - א, ב, ג |
| `add_heading(doc, text)` | כותרת-משנה (Heading 2) |
| `add_heading3(doc, text)` | כותרת משנה-משנה (Heading 3) |
| `add_quote(doc, text)` | ציטוט (Quote) |
| `add_exhibit_ref(doc, text)` | שורת נספח (Subtitle) |
| `add_plain(doc, text)` | פסקת Normal ללא מספור |
| `add_table(doc, headers, rows, widths, header_bold, style)` | טבלת RTL |
| `add_run(p, text, bold, underline)` | run בודד עם RTL (פרימיטיב) |
| `add_formatted_text(p, text, underline)` | טקסט עם הדגשות inline |
| `apply_paragraph_underline(p)` | קו תחתון לפסקה שלמה |
| `set_numbering(p, num_id, ilvl=0)` | החלת numPr מפורש |
| `sanitize_source_text(t)` | ניקוי LRM/RLM + מקפים ארוכים |
| `save(doc, path)` | שמירה |

## שלושה עקרונות קריטיים

**1. RTL ברמת ה-run.** סגנונות בתבנית עלולים לשאת `<w:rtl w:val="0"/>` שמכבה RTL,
ולכן **כל run מקבל `<w:rtl/>` מפורש** שדורס זאת. אחרת Word מתייחס לעברית כ-LTR
ומציג אותה בפונט ה-ascii במקום David. טקסט מודגש מקבל גם `<w:bCs/>`, כי עברית
מתבלטת רק כך. `add_run` עושה את כל זה.

**2. אין לקבוע `rFonts` או `sz` ברמת ה-run.** סגנון `Normal` מפריד בין השפות
(עברית David 12 דרך `szCs`, אנגלית Times New Roman 10 דרך `sz`), וכל קביעה ברמת
ה-run תשבור את גודל האנגלית.

**3. אין לקבוע `w:jc` בפסקה שבתוך תא טבלה.** ב-OOXML הערכים `left`/`right` הם
כינויים של `start`/`end`, ו-Word ממפה `right` ל-`end`. בפסקה עם `<w:bidi/>` הקצה
הוא **צד שמאל**, ולכן `jc=right` מיישר שמאלה. בלי `w:jc` התא יורש מ-`Normal` את
`jc=both`, שהוא היישור הנכון. אומת במדידה על PDF: תא בלי `w:jc` הציב את הטקסט
5 נקודות מהקצה הימני, ותא עם `jc=right` הציב אותו 101 נקודות משם.

## הוספת יכולות חדשות

כל יכולת עיצוב או בנייה חדשה מתווספת **כאן**, לא בסקיל הצרכן, כדי שתהיה זמינה
לכולם. סקיל שמגלה שחסרה לו יכולת צריך להרחיב את המנוע ולא לעקוף אותו.
