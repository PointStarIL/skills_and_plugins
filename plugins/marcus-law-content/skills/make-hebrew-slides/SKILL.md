---
name: make-hebrew-slides
description: "יוצר, קורא ועורך מצגות PowerPoint (.pptx) בעברית בעיצוב מודרני-מאופק לקהל משפטי: פונטים Suez One (כותרות) ו-Rubik (גוף) מוטמעים, Complex Script typeface ל-RTL נכון, ואופציה לתמונות AI דרך kie.ai (שקף תמונה מלא או טקסט-עם-תמונה-בצד). הפעל כאשר: בקשה ליצור/לערוך מצגת בעברית, 'מצגת', 'pptx', 'שקפים', 'presentation'."
metadata:
  version: "1.0.0"
---

# מצגות עברית בסגנון מקצועי-משפטי

סקייל זה תומך בארבעה תרחישים: **יצירת מצגת חדשה**, **קריאת מצגת קיימת**, **עריכת מצגת קיימת**, ו**הוספת תמונות AI** למצגת, הכל עם עיצוב אחיד, פונטים יפים מ-Google Fonts, וטיפול נכון ב-RTL ו-Complex Script.

---

## 1. מערכת העיצוב (Design System)

### פלטת צבעים, Navy + Warm Accent

| תפקיד | קוד | הערה |
|---|---|---|
| נייבי עמוק (פריימרי) | `#0E2A47` | קווים, רקעי כותרת, טקסט הדגשה |
| שנהב חמים (רקע) | `#F5F1EA` | רקע כל השקפים |
| כמעט-שחור (טקסט) | `#1F1F1F` | טקסט גוף על רקע בהיר |
| זהב מאופק (אקסנט) | `#B8860B` | אלמנט מותג, מפרידי סקציות, callouts |
| אפור צפחה (משני) | `#5A6B7D` | טקסט משני, פוטר, מספרי שקפים |

### טיפוגרפיה (Google Fonts)

- **כותרות**: Suez One, 36pt, נייבי `#0E2A47`, מיושר לימין, RTL, פונט תקיף בסגנון משפטי-מודרני
- **גוף**: Rubik, 24pt, כמעט-שחור `#1F1F1F`, מיושר לימין, RTL, סנס-סריף נקי וקריא
- **פוטר**: Rubik 12pt, אפור צפחה `#5A6B7D`

> **חשוב**: בשקפים עם הרבה טקסט יש להוריד את גודל הגוף ל-18-22pt לפי הצורך.

### לאיוט קבוע לכל שקף

1. רקע שנהב מלא
2. בראש: קו דק נייבי באורך מלא, גובה 3pt
3. בפינה הימנית-עליונה: ריבוע זהב קטן (~12×12pt), מוטיב מותגי
4. כותרת השקף מתחת לקו, מיושרת לימין
5. גוף הטקסט מתחת לכותרת
6. פוטר: שם המרצה משמאל, מספר שקף מימין

---

## 2. כללי RTL ו-Complex Script, חובה!

הסיבה לסקייל הזה היא ש-python-pptx **לא** מטפל אוטומטית ב-RTL ולא ב-cs typeface. בלי טיפול נכון, התוצאה נראית שבורה. הכללים:

### א. כיוון פיסקה, `rtl="1"` ב-XML

הפונקציה `set_paragraph_rtl()` מוסיפה `<a:pPr rtl="1">`. בלי זה, סוגריים `(הודעה)` יוצגו בכיוון הפוך.

### ב. **Complex Script typeface (cs), קריטי לעברית!**

פונקציה: `set_run_complex_font(run, typeface)`.

PowerPoint בוחר את הפונט עבור עברית לפי `<a:cs typeface="...">`, **לא** לפי `<a:latin>`. בלי הגדרת cs, גם אם נציין `run.font.name = "Suez One"`, PowerPoint יציג עברית בברירת המחדל של המערכת (לרוב Calibri).

**תמיד** להשתמש ב-`set_run_complex_font(run, typeface)` אחרי `run.font.name = typeface`.

הפונקציות הציבוריות של `HebrewLegalDeck` מטפלות בזה אוטומטית.

### ג. רווח אחרי מספר ברשימה ממוספרת

הפונקציה `format_numbered_text(number, text)` מבטיחה `"1. שורה"` ולא `"1.שורה"`.

### ד. סימון ריצה כעברית

`set_run_lang_he(run)` מוסיף `lang="he-IL"`, משפר רינדור.

---

## 3. יצירת מצגת חדשה

```python
from scripts.pptx_builder import HebrewLegalDeck

deck = HebrewLegalDeck(
    lecturer_name='עו"ד שרית ואדה',
    output_path="/path/to/output.pptx",
)

deck.add_title_slide(
    title="ביקורת מנהלית על החלטות מוסדות תכנון",
    subtitle="הרצאה בלשכת עורכי הדין",
)
deck.add_content_slide(
    title="עילות הביקורת",
    bullets=["חוסר סבירות (הודעה)", "שיקולים זרים", "פגיעה בכללי הצדק הטבעי"],
)
deck.add_section_divider("חלק שני: דוגמאות מהפסיקה")
deck.save()
```

הפונקציות הציבוריות:

- `add_title_slide(title, subtitle=None)`, פתיחה
- `add_content_slide(title, bullets)`, כותרת + בולטים
- `add_numbered_slide(title, items)`, רשימה ממוספרת
- `add_two_column_slide(title, left_title, left_items, right_title, right_items)`, השוואה
- `add_quote_slide(quote, source)`, ציטוט
- `add_section_divider(title)`, מפריד נייבי
- `add_image_full_slide(image_path, title=None, caption=None)`, שקף תמונה גדולה (אספקט 16:9 מומלץ)
- `add_content_slide_with_image(title, bullets, image_path, image_side="left")`, כותרת + טקסט בצד אחד + תמונה בצד השני (אספקט 1:1 או 4:3 מומלץ)
- `add_blank_slide()`, לעריכה ידנית
- `save()`, שמירה

---

## 4. הטמעת הפונטים בתוך ה-PPTX

לאחר יצירת המצגת, להטמיע את הפונטים כדי שיוצגו נכון על מחשבי-קצה שאין בהם Suez One/Rubik:

```python
from scripts.embed_fonts import embed_fonts
from pathlib import Path

fonts_dir = Path(__file__).parent / "fonts"
embed_fonts(
    "/path/to/output.pptx",
    fonts={
        "Suez One": {"regular": str(fonts_dir / "SuezOne-Regular.ttf")},
        "Rubik": {
            "regular": str(fonts_dir / "Rubik-Regular.ttf"),
            "bold": str(fonts_dir / "Rubik-Bold.ttf"),
        },
    },
)
```

המודול `embed_fonts.py`:
- מוסיף את קבצי הפונט ל-`ppt/fonts/` בתוך ה-ZIP
- מצפין את כותרת ה-TTF לפי תקן OOXML (הופך ל-`.fntdata`)
- רושם MIME type ב-`[Content_Types].xml`
- מוסיף `<p:embeddedFontLst>` ל-`presentation.xml`

תוצאה: כל מי שיפתח את המצגת יראה את הפונטים, גם בלי להתקין אותם במחשב.

---

## 5. הוספת תמונות AI דרך kie.ai

### 5.1 כללי שימוש בתמונות במצגות משפטיות

תמונות AI אינן מתאימות לכל שקף במצגת משפטית. השתמש בהן רק כשהן **תורמות**, ולא כקישוט. לעיתים כדאי, ולעיתים פחות.

**שתי אפשרויות עיצוב:**

| סוג שקף | מתי להשתמש | איך |
|---|---|---|
| **תמונה לשקף מלא** (`add_image_full_slide`) | פתיחת סקציה, אילוסטרציה ויזואלית גדולה, שער למצגת | יצירת תמונה ב-aspect_ratio="16:9" |
| **תמונה בצד טקסט** (`add_content_slide_with_image`) | המחשת רעיון בצד בולטים, אייקון מושגי | יצירת תמונה ב-aspect_ratio="1:1" או "4:3" |

### 5.2 כלל החלטה מחייב, שאל את חיים לפני יצירת תמונה

**אסור** ליצור תמונות אוטומטית למצגת בלי לשאול. גם אם נתבקש "תוסיף תמונות", תמיד חיים יחליט מה מתאים.

הזרימה המחייבת:

1. בעת בניית מצגת, **לפני** קריאה ל-`generate_image`, לשאול את חיים:
   - באיזה שקף הוא רוצה תמונה
   - האם תמונה לשקף מלא או תמונה בצד הטקסט
   - איזה מודל (אם לא מצוין, להציע imagen4-fast כברירת מחדל)
   - לתת תיאור מילולי (prompt) שאתה מציע, לאישורו

2. רק אחרי אישור, לקרוא ל-`generate_image`.

3. אחרי יצירת התמונה, להראות את הנתיב המקומי לחיים, ולשאול אם הוא רוצה לראות אותה לפני הכנסתה למצגת.

> **שתי אזהרות שחובה לקרוא לפני יצירת תמונה כלשהי:**
> - **סעיף 5.5**, התמונה חייבת להיות רלוונטית לתוכן הספציפי של השקף, לא איור משפטי גנרי.
> - **סעיף 5.7**, אסור לייצר תמונות עם טקסט עברי כברירת מחדל; אם המשתמש מבקש במפורש, נדרשת בדיקה כפולה ושלישית, מודלים גנרטיביים נכשלים בעברית.

### 5.3 הקריאה ל-API

```python
from scripts.image_generator import generate_image

# תמונה לשקף מלא (16:9)
img_full = generate_image(
    prompt="A modern minimalist illustration of justice scales in deep navy "
           "and warm gold colors, on a cream background. Professional, "
           "no text, no specific religious or national symbols.",
    aspect_ratio="16:9",
    model="google/imagen4-fast",  # או None לברירת מחדל
    output_dir="/path/to/output_dir/images",
    filename="justice_scales.png",
)

# שילוב במצגת
deck.add_image_full_slide(
    image_path=img_full,
    title="עקרונות הצדק הטבעי",
    caption=None,  # אופציונלי
)
```

```python
# תמונה בצד טקסט (1:1)
img_side = generate_image(
    prompt="...",
    aspect_ratio="1:1",
    output_dir="/path/to/output_dir/images",
)

deck.add_content_slide_with_image(
    title="עילות הביקורת",
    bullets=["חוסר סבירות", "שיקולים זרים", "פגיעה בצדק הטבעי"],
    image_path=img_side,
    image_side="left",  # ב-RTL הטקסט מימין, התמונה משמאל
)
```

### 5.4 מודלים זמינים (kie.ai)

הפרמטר `model` בקריאה ל-`generate_image`:

| מודל | מתי לבחור | אספקט |
|---|---|---|
| `google/imagen4-fast` *(ברירת מחדל)* | רוב המקרים, איכות גבוהה ומהירות טובה | 16:9, 9:16, 1:1, 4:3, 3:4 |
| `google/imagen4` | איכות יותר גבוהה, איטי יותר | אותם אספקטים |
| `google/imagen4-ultra` | האיכות הגבוהה ביותר של Google | אותם אספקטים |
| `google/nano-banana` | זול ומהיר במיוחד, איכות סבירה | משתמש ב-`image_size` |
| `bytedance/seedream-v4-text-to-image` | סגנון אומנותי, "Seedream" | משתמש ב-`image_size` |
| `openai/gpt-image-2` | טוב במיוחד כשצריך טקסט בתוך התמונה | פיקסלים (1024×1024 וכד') |

המודול ממפה את `aspect_ratio` (סטרינג כמו "16:9") אוטומטית לפרמטר הנכון של כל מודל.

### 5.5 התמונה חייבת להיות רלוונטית לתוכן השקף, לא קישוט גנרי

**זוהי הוראה קריטית.** השקפים שמצוין שכדאי להוסיף בהם תמונה הם בדרך כלל שקפי מפתח (פתיחה, מפריד סקציה, רעיון מרכזי). תמונה גנרית של "פטיש משפט" או "מאזני צדק" שמופיעה ליד שקף שעוסק במשהו ספציפי, חוק התכנון, היטל השבחה, ביטוח לאומי, מוסיפה רעש ולא ערך.

**הכלל המחייב:**

לפני שאתה כותב prompt, **קרא את הטקסט בשקף** (כותרת + בולטים + caption אם יש), וזהה את **הרעיון הספציפי** שהשקף מעביר. ה-prompt חייב לתאר ויזואלית את הרעיון הזה, לא רעיון גנרי על "משפט".

**דוגמאות, שקף ספציפי, prompt רלוונטי:**

| תוכן השקף | prompt גרוע (גנרי) | prompt טוב (רלוונטי) |
|---|---|---|
| "תהליך הגשת ערר לוועדת ערר תכנון ובניה" | "scales of justice, gavel" | "modern minimalist illustration of a multi-stage flow with three icons: a building blueprint, a document being filed, a panel of three figures reviewing, navy and gold accents, cream background, no text" |
| "היטל השבחה, תמ"א 38/2 ופטור חניה" | "courthouse columns, judges" | "modern minimalist illustration of a residential building under renovation with scaffolding, calculator and coins beside it, navy and gold accents, cream background, no text" |
| "פגיעה שמיעה תעסוקתית, ביטוח לאומי" | "law books, gavel" | "modern minimalist illustration of an audiogram chart on the left with a stylized human ear on the right, navy and gold accents, cream background, no text" |
| "סדר הדין בערכאת ערעור" | "lady justice, blindfolded" | "modern minimalist illustration of an upward staircase with three steps, each labeled with a small icon (initial, first appeal, supreme), navy and gold accents, cream background, no text" |

**זרימת העבודה החובה:**

1. לפני כל קריאה ל-`generate_image`, להציג למשתמש את **תוכן השקף** (כותרת + בולטים) שאתה הולך לאייר.
2. להציע prompt **שמתייחס ספציפית** לתוכן זה, לא "תמונה משפטית גנרית".
3. אם הרעיון בשקף מופשט מדי לויזואליזציה (למשל "נימוקי בית המשפט"), **להציע למשתמש לוותר על תמונה בשקף הזה** ולא להמציא איור גנרי שאינו תורם.
4. לוותר גם כשהמשתמש מבקש "תוסיף תמונות" באופן כללי, ולהסביר שלא לכל שקף יש איור רלוונטי טבעי.

**עקרון מנחה:** אם אדם זר ביקש לתאר את התמונה בלי לראות את הטקסט בשקף, הוא צריך לזהות שהיא קשורה לאותו נושא ספציפי. אם הוא יכול לזהות רק "משהו משפטי כללי", התמונה לא טובה.

### 5.6 עקרונות לכתיבת prompt טוב למצגת משפטית

1. **באנגלית**, המודלים נותנים תוצאות טובות יותר באנגלית, גם אם המצגת בעברית.
2. **התאמת צבעים לפלטה של המצגת**, `"deep navy blue, warm gold, cream background"` ישתלב טוב.
3. **סגנון מינימליסטי-מודרני**, `"modern minimalist illustration"`, `"clean professional"`, `"sophisticated"`.
4. **בלי סמלים בעייתיים**, להימנע מ-`"specific country flag"`, `"specific religious symbol"` אלא אם רלוונטי.
5. **התאם לאספקט**, לתמונה בצד טקסט (1:1), prompt יותר ממוקד; לתמונה מלאה (16:9), אפשר לתאר סצנה רחבה יותר.

**דוגמה לפרומפט מצוין למצגת משפטית:**

> *"A modern, minimalist illustration of a courtroom gavel resting on a wooden desk, with soft warm light, deep navy blue and gold accents, cream background. Professional, sophisticated, suitable for a legal lecture slide. No text, no specific country symbols, photorealistic but stylized."*

### 5.7 טקסט בעברית בתוך תמונות, אסור כברירת מחדל

מודלים גנרטיביים (כולל imagen4 ו-gpt-image-2) **לא יודעים לכתוב עברית** ברמה אמינה. אותיות יוצאות הפוכות, מנוקדות באופן שגוי, מומצאות, או נראות כעברית אבל אינן עברית כלל. תמונה כזו במצגת משפטית, שתוצג בלשכת עורכי הדין או בפני ועדה, היא נזק תדמיתי.

**הכלל הברירת מחדל:**

בכל קריאה ל-`generate_image`, תמיד להוסיף לפרומפט: `"no text, no labels, no Hebrew letters, no writing of any kind"`.

**אם המשתמש מבקש במפורש טקסט עברי בתוך התמונה** (למשל "יוצר באנר עם המילה 'צדק'"):

זוהי בקשה בסיכון גבוה. נדרשת בדיקה כפולה ושלושה, לא משלוח לאישור אחרי הניסיון הראשון:

1. **ניסיון ראשון**, להריץ עם הפרומפט.
2. **בדיקה ויזואלית קפדנית** של התמונה שחזרה:
   - לפתוח את הקובץ עם `view` ולקרוא את הטקסט אות-אחר-אות
   - לוודא שכל אות נכונה ובסדר נכון (מימין-לשמאל)
   - לוודא שאין אותיות הפוכות, חסרות, או "אותיות שנראות עבריות" אבל אינן
   - לוודא שאין ניקוד שגוי או שאריות מילים אחרות
3. **לפחות 2-3 ניסיונות חוזרים** עם וריאציות של הפרומפט, גם אם הניסיון הראשון נראה תקין, מודלים גנרטיביים נוטים להוציא טקסט שבמבט ראשון נראה תקין אבל בעיון שני יוצא שגוי.
4. **להציג למשתמש את כל הוריאציות** ולתת לו לבחור, לעולם לא להחליט לבד שהטקסט "נראה בסדר".
5. אם אחרי 3 ניסיונות אין תוצאה תקינה, להציע למשתמש להוסיף את הטקסט העברי בעריכה ידנית ב-PowerPoint **מעל** התמונה (להוציא את הטקסט מהפרומפט ולהשאיר רק את האיור).

**טקסט באנגלית** בתוך תמונה (למשל "JUSTICE" על פטיש שופט), בדרך כלל יוצא תקין, אבל גם שם רצוי לבדוק פעם אחת לפני אישור.

### 5.8 מפתח ה-API

מפתח ה-API של kie.ai שמור בקובץ `scripts/config.py`. ניתן לדרוס דרך משתנה הסביבה `KIE_API_KEY`.

---

## 6. קריאה ועריכה של מצגת קיימת

```python
from scripts.pptx_editor import HebrewPptxReader, HebrewPptxEditor

reader = HebrewPptxReader("/path/to/existing.pptx")
print(reader.summary())

editor = HebrewPptxEditor("/path/to/existing.pptx")
editor.update_slide_title(2, "כותרת חדשה")
editor.find_and_replace("ישן", "חדש")
editor.apply_design_system_all()  # החלת המערכת על מצגת קיימת
editor.save("/path/to/updated.pptx")
```

---

## 7. בדיקה ויזואלית

תמיד ליצור PDF ולוודא ויזואלית:

```bash
soffice --headless --convert-to pdf /path/to/file.pptx --outdir /tmp/
pdftoppm /tmp/file.pdf /tmp/slide -png -r 100
```

לבדוק במיוחד:
1. **סוגריים**, `(הודעה)` עם הסוגר הפותח מימין
2. **רשימות ממוספרות**, `1. שורה` (עם רווח)
3. **פונטים**, Suez One בכותרות, Rubik בגוף
4. **יישור**, RTL נכון
5. **תמונות**, אם יש, ממורכזות, לא חורגות מהשוליים, אספקט מקורי נשמר

---

## קבצים בסקייל

- `scripts/pptx_builder.py`, יצירת מצגות חדשות (HebrewLegalDeck, כולל שקפי תמונה)
- `scripts/pptx_editor.py`, קריאה ועריכה של מצגות קיימות
- `scripts/embed_fonts.py`, הטמעת פונטים בתוך PPTX
- `scripts/image_generator.py`, יצירת תמונות AI דרך kie.ai (KieImageGenerator + generate_image)
- `scripts/config.py`, הגדרות (KIE_API_KEY, מודל ברירת מחדל, timeouts)
- `fonts/`, קבצי TTF של Suez One ו-Rubik (מ-Google Fonts, רישיון OFL)
- `references/design_system.md`, פירוט מערכת העיצוב
- `references/rtl_deep_dive.md`, הסבר טכני על RTL ו-cs typeface

ראה `INSTALL.md` להוראות התקנה ב-Windows.
