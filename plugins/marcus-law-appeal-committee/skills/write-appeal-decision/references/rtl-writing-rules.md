# כללי כתיבה ב-RTL בעברית עבור מסמכי DOCX

מסמך זה הוא המדריך המוסמך של הפלאג-אין לכל מה שקשור לעיצוב RTL בעברית. כל קובץ DOCX שהסקיל יוצר, חייב לעמוד בכללים אלה ללא יוצא מן הכלל. מסמך משפטי בעברית חייב להיות מוצג נכון מימין לשמאל, אחרת הוא לא יוכל לשמש כתחליף לטיוטה הקיימת.

## תוכן עניינים

- עיקרון יסוד: RTL הוא חובה, לא ברירה
- רכיב 1: הגדרת הפסקה כ-RTL (bidi)
- רכיב 2: יישור הפסקה לימין
- רכיב 3: פונט עברי תקני
- רכיב 4: גודלים סטנדרטיים
- רכיב 5: מרווחי שורות
- רכיב 6: שוליים סטנדרטיים
- רכיב 7: כיוון העמוד והסקציה
- רכיב 8: רשימה ממוספרת ב-RTL
- רכיב 9: רצף תווים מעורב (עברית + מספרים + אנגלית)
- רכיב 10: טבלאות ב-RTL
- רכיב 11: הפרדה בין סוגי תוכן
- רכיב 12: הימנעות משגיאות נפוצות
- רכיב 13: בדיקת איכות סופית
- דוגמת קוד מלאה ליצירת פסקה מושלמת
- רכיב 14: עריכת DOCX קיים
- סיכום

## עיקרון יסוד: RTL הוא חובה, לא ברירה

כל מסמך, כל פסקה, כל טבלה, כל ריצה (run) של טקסט, וכל סקציה (section) במסמכי DOCX שהפלאג-אין יוצר חייבים להיות מוגדרים מפורשות כ-RTL. python-docx לא מגדיר RTL כברירת מחדל, ולכן יש להפעיל זאת ידנית בכל אובייקט.

## רכיב 1: הגדרת הפסקה כ-RTL (bidi)

לכל פסקה (paragraph) יש להוסיף את האלמנט `<w:bidi w:val="1"/>` בתוך `<w:pPr>`. זה אומר ל-Word שהפסקה כתובה משמאל-לימין הפוך, היינו ימין-לשמאל. בלי זה, הטקסט אולי ייראה בעברית אבל הפסקה עצמה תיחשב כ-LTR ויהיו בעיות בכיוון הטקסט.

קוד פייתון:

```python
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

def set_rtl_paragraph(paragraph):
    pPr = paragraph._p.get_or_add_pPr()
    bidi = OxmlElement('w:bidi')
    bidi.set(qn('w:val'), '1')
    pPr.append(bidi)
```

## רכיב 2: יישור הפסקה לימין

חוץ מ-bidi, יש לקבוע את היישור של הפסקה. ארבע אופציות:

- `WD_ALIGN_PARAGRAPH.RIGHT` יישור לימין. מתאים לכותרות, לפסקת פתיחה, לפסקאות קצרות.
- `WD_ALIGN_PARAGRAPH.JUSTIFY` יישור דו-צדדי. מתאים לפסקאות גוף ארוכות. ב-RTL זה אומר שהשורה האחרונה ביישור לימין.
- `WD_ALIGN_PARAGRAPH.CENTER` יישור למרכז. מתאים לכותרת ראשית של המסמך.
- `WD_ALIGN_PARAGRAPH.LEFT` לא לשימוש במסמך עברי, אלא אם יש סיבה ספציפית (מספר אנגלי בלבד, וכדומה).

החלטה לפי סוג הפסקה:

- פסקת גוף: JUSTIFY (מתאים למסמך משפטי).
- כותרת ראשית של המסמך: CENTER.
- כותרת בלוק / כותרת משנה: RIGHT.
- חתימה / תאריך: RIGHT.

## רכיב 3: פונט עברי תקני

הפונט הסטנדרטי במסמכים משפטיים בעברית הוא **David**. אופציות חלופיות: FrankRuehl, Miriam, Narkisim, Arial. אבל היצמדות ל-David היא הסטנדרט.

חשוב: ב-DOCX, יש להגדיר את הפונט בשלוש מקומות:

1. `w:ascii` הפונט לתווים אנגליים.
2. `w:hAnsi` הפונט לתווים אנגליים-הרחבה.
3. `w:cs` (Complex Script) הפונט לעברית, ערבית, ופונטים מורכבים אחרים.

בנוסף, יש להגדיר `w:hint="cs"` כדי שWord יבחר את ה-Complex Script font כברירת מחדל.

קוד פייתון:

```python
def set_run_font(run, font_name="David", size_pt=12, bold=False):
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts')
        rPr.append(rFonts)
    rFonts.set(qn('w:ascii'), font_name)
    rFonts.set(qn('w:hAnsi'), font_name)
    rFonts.set(qn('w:cs'), font_name)
    rFonts.set(qn('w:hint'), 'cs')
    sz = rPr.find(qn('w:sz'))
    if sz is None:
        sz = OxmlElement('w:sz')
        rPr.append(sz)
    sz.set(qn('w:val'), str(int(size_pt * 2)))
    szCs = rPr.find(qn('w:szCs'))
    if szCs is None:
        szCs = OxmlElement('w:szCs')
        rPr.append(szCs)
    szCs.set(qn('w:val'), str(int(size_pt * 2)))
```

ה-szCs קריטי. בלעדיו, גודל הטקסט בעברית עשוי להיראות שגוי, גם אם הפונט נכון.

## רכיב 4: גודלים סטנדרטיים

- **גוף המסמך:** David 12pt (24 ב-DOCX, שזה חצי-נקודה).
- **כותרת ראשית:** David 16pt מודגש.
- **כותרת בלוק / סעיף:** David 13-14pt מודגש.
- **כותרת משנה:** David 12-13pt מודגש.
- **הערות שוליים:** David 10pt.
- **טבלת הוצאות / טבלת מספרים:** David 11pt.

## רכיב 5: מרווחי שורות

- **גוף המסמך:** מרווח 1.5 (פי-אחד וחצי).
- **טבלאות:** מרווח 1.15 או 1.0.
- **הערות / הערת שוליים:** מרווח 1.0.

קוד פייתון:

```python
from docx.enum.text import WD_LINE_SPACING

paragraph.paragraph_format.line_spacing = 1.5
# או:
paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
paragraph.paragraph_format.line_spacing = 1.5
```

## רכיב 6: שוליים סטנדרטיים

שוליים של 2.54 ס"מ (1 אינץ') מכל הצדדים, או 2.5 ס"מ אם המסמך ארוך מאוד. זה הסטנדרט במשרדי עורכי דין בישראל.

```python
from docx.shared import Cm

for section in doc.sections:
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(2.54)
    section.right_margin = Cm(2.54)
```

## רכיב 7: כיוון העמוד והסקציה

חוץ מהגדרת bidi בכל פסקה, יש להגדיר גם את כיוון הסקציה כ-RTL. זה משפיע על:

- מספור עמודים (יוצג מימין לשמאל).
- כותרות ראשיות.
- מספור הערות שוליים.

קוד פייתון:

```python
def set_rtl_section(section):
    sectPr = section._sectPr
    bidi = sectPr.find(qn('w:bidi'))
    if bidi is None:
        bidi = OxmlElement('w:bidi')
        sectPr.append(bidi)
```

## רכיב 8: רשימה ממוספרת ב-RTL

רשימות ממוספרות בעברית מתחילות מימין. הסימן (1., 2., 3.) צריך להופיע בצד ימין של הפסקה, והטקסט אחריו זורם משמאל.

עבור הוועדה, המספור הוא לרוב 1, 2, 3 (ספרות ערביות), אבל לעיתים גם אותיות עבריות (א., ב., ג.). הסקיל יבחר לפי הפורמט שהמשתמש כותב בטיוטה.

ב-python-docx, רשימה ממוספרת דורשת:

1. שימוש בסגנון 'List Number' או 'List Paragraph'.
2. הגדרת bidi בפסקה.
3. וידוא שה-numbering definition (numId) תומך ב-RTL.

לרוב המסמכים, פתרון פשוט יותר הוא לכתוב את המספור ידנית בטקסט ("1. ", "2. ") ולא להשתמש ב-auto-numbering. זה מבטל בעיות תאימות ב-Word על מערכות שונות.

## רכיב 9: רצף תווים מעורב (עברית + מספרים + אנגלית)

כשמשולבים בטקסט עברי גם מספרים, סוגריים, תאריכים, או מילים באנגלית, ה-bidi של הפסקה יטפל ברצף נכון. עם זאת, יש מקרים פינתיים:

- **תאריכים:** "14.9.2025" יוצג נכון רק אם הפסקה מוגדרת bidi. אחרת המספרים עשויים להופיע משמאל לימין.
- **שמות בלועזית:** "ב-DOCX" יוצג כראוי עם רנדור bidi.
- **סוגריים:** סוגריים פותחים וסוגרים יוחלפו אוטומטית בהתאם לכיוון (סוגר שמאלי בעברית הוא הסוגר הימני).
- **גרשיים:** עדיף להשתמש בגרשיים ישרים (" " ולא " ") לצורך תאימות.

## רכיב 10: טבלאות ב-RTL

טבלאות עבריות יוצרות בעיה ספציפית: סדר העמודות צריך להיות מימין לשמאל, אך python-docx יוצר טבלאות LTR כברירת מחדל.

לטיפול בכך:

```python
def set_rtl_table(table):
    tblPr = table._element.tblPr
    bidiVisual = OxmlElement('w:bidiVisual')
    bidiVisual.set(qn('w:val'), '1')
    tblPr.append(bidiVisual)
    for row in table.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                set_rtl_paragraph(p)
```

ה-`bidiVisual` הוא מה שהופך את הטבלה לכיוון RTL.

## רכיב 11: הפרדה בין סוגי תוכן

המסמך עשוי להכיל סוגים שונים של תוכן, וכל אחד דורש סגנון משלו:

| סוג תוכן | פונט | גודל | יישור | מרווח |
|---|---|---|---|---|
| כותרת ראשית | David Bold | 16 | מרכז | 1.5 |
| כותרת בלוק | David Bold | 13 | ימין | 1.5 |
| גוף הפסקה | David | 12 | justify | 1.5 |
| ציטוט פסיקה | David | 11 | justify | 1.15 |
| הערה / footnote | David | 10 | ימין | 1.0 |
| תאריך וחתימה | David Bold | 12 | ימין | 1.0 |

## רכיב 12: הימנעות משגיאות נפוצות

1. **לא להשתמש ב-`paragraph.add_run().font.complex_script = True`** כי זה לא קיים ב-python-docx. במקום זה, יש להשתמש בקוד שמוצג בהמשך.

2. **לא לשכוח את `w:szCs`** בנוסף ל-`w:sz`. בלעדיו, גודל הפונט בעברית עשוי להיות שונה מהמיועד.

3. **לא להשתמש ב-`'Times New Roman'`** כפונט ברירת מחדל. הוא תומך בעברית פיזית, אבל מסמכים משפטיים בישראל לא משתמשים בו.

4. **לא להגדיר רק את `w:bidi` בלי `WD_ALIGN_PARAGRAPH`** ולהיפך. שניהם חייבים להופיע יחד.

5. **לא לערבב סגנונות built-in של Word עם RTL ידני.** אם משתמשים ב-`doc.add_heading()`, יש להחיל את ה-RTL על הפסקה שנוצרה.

## רכיב 13: בדיקת איכות סופית

הסקיל לפני שמירת הקובץ ייצור צ'קליסט:

1. כל פסקה מוגדרת bidi? כן או לא.
2. כל פסקה ביישור נכון (לרוב JUSTIFY או RIGHT)?
3. הפונט David מופיע ב-3 מקומות (ascii, hAnsi, cs)?
4. גודל מופיע ב-2 מקומות (sz, szCs)?
5. השוליים 2.54 ס"מ?
6. מרווח שורות 1.5 (אלא אם הוגדר אחרת)?
7. ה-section עצמו ב-RTL?
8. אם יש טבלאות: bidiVisual מוגדר?

ניתן להשתמש בסקריפט `scripts/docx_rtl_helper.py` שכולל פונקציות מוכנות לכל אחד מהרכיבים, כדי להבטיח עקביות.

## דוגמת קוד מלאה ליצירת פסקה מושלמת

```python
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


def set_rtl_paragraph(paragraph):
    pPr = paragraph._p.get_or_add_pPr()
    bidi = OxmlElement('w:bidi')
    bidi.set(qn('w:val'), '1')
    pPr.append(bidi)


def set_run_font(run, font_name="David", size_pt=12, bold=False):
    run.font.bold = bold
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts')
        rPr.append(rFonts)
    rFonts.set(qn('w:ascii'), font_name)
    rFonts.set(qn('w:hAnsi'), font_name)
    rFonts.set(qn('w:cs'), font_name)
    rFonts.set(qn('w:hint'), 'cs')
    for tag in ['w:sz', 'w:szCs']:
        el = rPr.find(qn(tag))
        if el is None:
            el = OxmlElement(tag)
            rPr.append(el)
        el.set(qn('w:val'), str(int(size_pt * 2)))
    if bold:
        for tag in ['w:b', 'w:bCs']:
            el = rPr.find(qn(tag))
            if el is None:
                el = OxmlElement(tag)
                rPr.append(el)


def add_para(doc, text, *, bold=False, size=12, align='justify', spacing=1.5):
    p = doc.add_paragraph()
    set_rtl_paragraph(p)
    if align == 'right':
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    elif align == 'center':
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    else:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.line_spacing = spacing
    r = p.add_run(text)
    set_run_font(r, "David", size, bold)
    return p
```

זוהי תבנית הבסיס. כל פסקה במסמך תיווצר באמצעות `add_para`, וכל פסקה תהיה אוטומטית RTL, ביישור ובפונט הנכונים.

## רכיב 14: עריכת DOCX קיים

כשהסקיל עורך DOCX קיים (לדוגמה, מחליף פסקה בטיוטה הקיימת), עליו לוודא שהפסקה החדשה שמוסיף מקבלת את אותם מאפייני RTL. עדיף לבדוק את הפסקה הקיימת ולחקות את מאפייניה, ולא להוסיף פסקה עם הגדרות חדשות שעלולות לשבור את הסגנון של המסמך.

קוד לחיקוי סגנון פסקה קיימת:

```python
def copy_paragraph_style(source_paragraph, target_paragraph):
    source_pPr = source_paragraph._p.find(qn('w:pPr'))
    if source_pPr is not None:
        from copy import deepcopy
        target_pPr = deepcopy(source_pPr)
        existing = target_paragraph._p.find(qn('w:pPr'))
        if existing is not None:
            target_paragraph._p.remove(existing)
        target_paragraph._p.insert(0, target_pPr)
```

## סיכום

כל מסמך DOCX שיוצר הפלאג-אין חייב להיות מוגדר במלואו כ-RTL, מבחינת:

1. כיוון פסקה (bidi).
2. יישור (RIGHT או JUSTIFY).
3. פונט (David ב-ascii, hAnsi, cs).
4. גודל (sz + szCs).
5. כיוון סקציה (bidi בסקציה).
6. שוליים (2.54 ס"מ).
7. מרווח שורות (1.5 לגוף).
8. טבלאות (bidiVisual אם יש).

הסקריפט `scripts/docx_rtl_helper.py` מספק את כל הפונקציות. הסקיל ישתמש בו לכל יצירה של DOCX.
