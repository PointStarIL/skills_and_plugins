# טכניקות DOCX מתקדמות למסמכים משפטיים בעברית

קובץ עיון זה מרכז את טכניקות ה-DOCX המתקדמות של הסקיל. נטען לפי צורך מ-SKILL.md.

## תוכן עניינים

- טבלאות RTL
- Tracked Changes - עקוב אחר שינויים
- הערות (Comments)
- עריכת DOCX קיים (Unpack → Edit → Pack)
- הערות שוליים (Footnotes)
- מרווח שורות (Line Spacing)
- תוכן עניינים (TOC)
- קו תחתי (Underline)
- מספר סקשנים (Multiple Sections)
- לוגו/תמונה בכותרת (Letterhead)
- היפרלינקים

## טבלאות RTL

**קריטי: `visuallyRightToLeft: true` - בלי זה העמודות יהיו הפוכות!**

```javascript
const { Table, TableRow, TableCell, BorderStyle, WidthType, ShadingType } = require('docx');

const CONTENT_WIDTH = 9072;  // A4 עם שוליים 2.5 ס"מ (11906 - 1417×2)
const border = { style: BorderStyle.SINGLE, size: 1, color: "999999" };
const borders = { top: border, bottom: border, left: border, right: border };
const noBorders = {
  top: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  bottom: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  left: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  right: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" }
};

// Helper function לתאים בעברית
const rtlCell = (text, width, opts = {}) => new TableCell({
  borders: opts.noBorders ? noBorders : borders,
  width: { size: width, type: WidthType.DXA },
  margins: { top: 80, bottom: 80, left: 120, right: 120 },
  ...(opts.shading ? { shading: { fill: opts.shading, type: ShadingType.CLEAR } } : {}),
  children: [new Paragraph({
    bidirectional: true,
    alignment: opts.alignment || AlignmentType.CENTER,
    children: [new TextRun({
      text, font: "David", size: 24, rightToLeft: true, bold: opts.bold
    })]
  })]
});

// טבלה עם גבולות
new Table({
  visuallyRightToLeft: true,  // קריטי! בלי זה העמודות הפוכות
  width: { size: CONTENT_WIDTH, type: WidthType.DXA },
  columnWidths: [4536, 2268, 2268],  // חייב להסתכם ל-CONTENT_WIDTH
  rows: [
    new TableRow({ children: [
      rtlCell("סוג שירות", 4536, { bold: true, shading: "D5E8F0" }),
      rtlCell("תעריף", 2268, { bold: true, shading: "D5E8F0" }),
      rtlCell("הערות", 2268, { bold: true, shading: "D5E8F0" }),
    ]}),
    new TableRow({ children: [
      rtlCell("ייעוץ משפטי", 4536),
      rtlCell("850 ש״ח", 2268),
      rtlCell("בתוספת מע״מ", 2268),
    ]}),
  ]
})

// טבלה ללא גבולות (לחתימות / header)
new Table({
  visuallyRightToLeft: true,
  width: { size: CONTENT_WIDTH, type: WidthType.DXA },
  columnWidths: [CONTENT_WIDTH / 2, CONTENT_WIDTH / 2],
  rows: [
    new TableRow({ children: [
      rtlCell("חתימה: ________", CONTENT_WIDTH / 2, { noBorders: true, alignment: AlignmentType.CENTER }),
      rtlCell("חתימה: ________", CONTENT_WIDTH / 2, { noBorders: true, alignment: AlignmentType.CENTER }),
    ]})
  ]
})
```

**כללים:**
- **`visuallyRightToLeft: true`** - חובה! בלי זה העמודות משמאל לימין
- **`WidthType.DXA`** - לא PERCENTAGE (פחות אמין ב-RTL)
- **`columnWidths`** - סכום חייב להיות שווה ל-`CONTENT_WIDTH`
- **`bidirectional: true` + `rightToLeft: true`** - בכל תא

---

## Tracked Changes - עקוב אחר שינויים

### שם מחבר בעברית
```xml
<w:del w:id="10" w:author="עו&quot;ד כהן" w:date="2026-02-06T09:00:00Z">
```

### שינוי ערך (סכום, תאריך, תקופה)
פצל את הטקסט ועטוף רק את הערך שמשתנה:
```xml
<w:r><w:rPr>...RTL PROPS...</w:rPr>
  <w:t xml:space="preserve">שכר הטרחה יעמוד על סך של </w:t></w:r>
<w:del w:id="10" w:author="עו&quot;ד כהן" w:date="...">
  <w:r><w:rPr>...RTL PROPS...</w:rPr><w:delText>750</w:delText></w:r>
</w:del>
<w:ins w:id="11" w:author="עו&quot;ד כהן" w:date="...">
  <w:r><w:rPr>...RTL PROPS...</w:rPr><w:t>850</w:t></w:r>
</w:ins>
<w:r><w:rPr>...RTL PROPS...</w:rPr>
  <w:t xml:space="preserve"> ש״ח לשעת עבודה</w:t></w:r>
```

### מחיקת סעיף שלם
סמן גם את ה-paragraph mark כ-deleted:
```xml
<w:p>
  <w:pPr>
    <w:bidi/>
    <w:jc w:val="both"/>
    <w:rPr>
      <w:del w:id="20" w:author="עו&quot;ד כהן" w:date="..."/>
    </w:rPr>
  </w:pPr>
  <w:del w:id="21" w:author="עו&quot;ד כהן" w:date="...">
    <w:r><w:rPr>...RTL PROPS...</w:rPr>
      <w:delText>הסעיף שנמחק</w:delText></w:r>
  </w:del>
</w:p>
```

### RTL PROPS - בלוק rPr מלא לכל run
```xml
<w:rPr>
  <w:rFonts w:ascii="David" w:cs="David" w:eastAsia="David" w:hAnsi="David"/>
  <w:sz w:val="24"/>
  <w:szCs w:val="24"/>
  <w:rtl/>
</w:rPr>
```

### קבלה/דחייה של שינויים

**קבלת Insertion:**
```
לפני: <w:ins w:id="5" w:author="..."><w:r>...<w:t>טקסט חדש</w:t></w:r></w:ins>
אחרי: <w:r>...<w:t>טקסט חדש</w:t></w:r>
→ הסר את תגית <w:ins> ושמור את התוכן הפנימי.
```

**דחיית Insertion:**
```
לפני: <w:ins w:id="5" w:author="..."><w:r>...<w:t>טקסט חדש</w:t></w:r></w:ins>
אחרי: (הסר לחלוטין)
→ מחק את כל בלוק ה-<w:ins> כולל תוכנו.
```

**קבלת מחיקה:**
```
לפני: <w:del w:id="10" w:author="..."><w:r>...<w:delText>טקסט שנמחק</w:delText></w:r></w:del>
אחרי: (הסר לחלוטין)
→ מחק את כל בלוק ה-<w:del> כולל תוכנו, המחיקה מתקבלת.
```

**שחזור טקסט מקורי (דחיית מחיקה):**
```
לפני: <w:del w:id="10" w:author="..."><w:r>...<w:delText>טקסט מקורי</w:delText></w:r></w:del>
אחרי: <w:r>...<w:t>טקסט מקורי</w:t></w:r>
→ הסר <w:del>, החלף <w:delText> ב-<w:t>, הסר <w:del> מ-rPr אם קיים.
```

---

## הערות (Comments)

הערות משמשות בסקירה משפטית להסביר *למה* בוצע שינוי:

```bash
python /mnt/skills/public/docx/scripts/comment.py unpacked/ 0 "הערה בעברית" --author "עו״ד כהן"
```

שימושים נפוצים:
- הסבר לשינוי סכום או תאריך
- דגל על סעיף בעייתי
- הפניה לפסיקה או חקיקה
- שאלה ללקוח / לצד השני

> **הערה:** `comment.py` מטפל אוטומטית ב-Content_Types ו-relationships.

---

## עריכת DOCX קיים (Unpack → Edit → Pack)

### תהליך מאומת
```bash
# 1. פתיחת הקובץ
python /mnt/skills/public/docx/scripts/unpack.py input.docx unpacked/

# 2. עריכת word/document.xml (או קבצי XML אחרים)

# 3. ארגון מחדש
python /mnt/skills/public/docx/scripts/pack.py unpacked/ output.docx --original input.docx
```

### מיקום הוספת תוכן - כלל קריטי
```
פסקאות חדשות חייבות להיכנס *לפני* <w:sectPr> האחרון בגוף המסמך.
הוספה *אחרי* sectPr תיכשל בוולידציה.

מבנה תקין:
  <w:body>
    <w:p>...</w:p>          ← פסקאות קיימות
    <w:p>...</w:p>          ← פסקה חדשה כאן     <w:sectPr>...</w:sectPr> ← תמיד אחרון
  </w:body>
```

### דוגמה - הוספת פסקה בעברית
```xml
<w:p>
  <w:pPr>
    <w:bidi/>
    <w:jc w:val="both"/>
  </w:pPr>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="David" w:cs="David" w:eastAsia="David" w:hAnsi="David"/>
      <w:sz w:val="24"/>
      <w:szCs w:val="24"/>
      <w:rtl/>
    </w:rPr>
    <w:t>הטקסט החדש</w:t>
  </w:r>
</w:p>
```

---

## הערות שוליים (Footnotes)

**השימוש המרכזי:** הפניות לחקיקה ופסיקה.

```javascript
const { FootnoteReferenceRun } = require('docx');

// 1. הגדרה ב-Document:
const doc = new Document({
  footnotes: {
    1: { children: [new Paragraph({
      bidirectional: true, alignment: AlignmentType.START,  // START
      children: [new TextRun({
        text: "חוק החוזים (חלק כללי), התשל״ג-1973, סעיף 12.",
        font: "David", size: 20, rightToLeft: true  // 10pt להערות שוליים
      })]
    })] },
    2: { children: [new Paragraph({
      bidirectional: true, alignment: AlignmentType.START,
      children: [new TextRun({
        text: "ע״א 1234/20 כהן נ׳ לוי, פסקה 15 (פורסם בנבו, 1.1.2024).",
        font: "David", size: 20, rightToLeft: true
      })]
    })] },
  },
  // ...sections
});

// 2. הפניה בגוף הטקסט:
new Paragraph({
  bidirectional: true, alignment: AlignmentType.BOTH,
  children: [
    new TextRun({ text: "חובת תום הלב", font: "David", size: 24, rightToLeft: true }),
    new FootnoteReferenceRun(1),
    new TextRun({ text: " חלה על כל שלבי המשא ומתן", font: "David", size: 24, rightToLeft: true }),
    new FootnoteReferenceRun(2),
    new TextRun({ text: ".", font: "David", size: 24, rightToLeft: true }),
  ]
})
```

### תיקון RTL בהערות שוליים (post-unpack)
docx-js לא מגדיר RTL מלא בהערות שוליים. אחרי unpack, צריך לתקן ב-`word/footnotes.xml`:
```xml
<!-- 1. הוסף pStyle + bidi לכל הערת שוליים: -->
<w:footnote w:id="1">
  <w:p>
    <w:pPr>
      <w:pStyle w:val="FootnoteText"/>
      <w:bidi/>
      <w:jc w:val="start"/>
    </w:pPr>
    ...

<!-- 2. הוסף rtl ל-footnoteRef run: -->
    <w:r>
      <w:rPr>
        <w:rStyle w:val="FootnoteReference"/>
        <w:rtl/>
      </w:rPr>
      <w:footnoteRef/>
    </w:r>
```

---

## מרווח שורות (Line Spacing)

**דרישת בתי המשפט:** בדרך כלל 1.5 שורות.

```javascript
const { LineRuleType } = require('docx');

// LineRuleType.AUTO, הערך הוא ב-1/240 שורה
spacing: { line: 240, lineRule: LineRuleType.AUTO }  // 1.0, צפוף
spacing: { line: 276, lineRule: LineRuleType.AUTO }  // 1.15, ברירת מחדל Word
spacing: { line: 360, lineRule: LineRuleType.AUTO }  // 1.5, נדרש בבתי משפט
spacing: { line: 480, lineRule: LineRuleType.AUTO }  // 2.0, כפול

// שילוב עם before/after:
spacing: { line: 360, lineRule: LineRuleType.AUTO, before: 120, after: 120 }
```

---

## תוכן עניינים (TOC)

**חובה: TOC ידני (לא TableOfContents).**
`TableOfContents` של docx-js מייצר שדה שוורד מעדכן ב-F9 ומאבד הגדרות RTL.

```javascript
const { Tab, TabStopType, LeaderType, PageBreak } = require('docx');

// שורת TOC ידנית
const tocEntry = (text, pageNum, opts = {}) => new Paragraph({
  bidirectional: true,
  spacing: { after: 60, line: 276, lineRule: LineRuleType.AUTO },
  ...(opts.indent ? { indent: { right: opts.indent } } : {}),
  tabStops: [{ type: TabStopType.RIGHT, position: 9026, leader: LeaderType.DOT }],
  children: [
    new TextRun({
      text, font: "David", size: 24, rightToLeft: true,
      bold: opts.bold || false,
    }),
    new TextRun({ children: [new Tab()], font: "David", rightToLeft: true }),
    new TextRun({
      text: String(pageNum), font: "David", size: 24, rightToLeft: true,
    }),
  ]
});

// שימוש:
new Paragraph({
  bidirectional: true, alignment: AlignmentType.CENTER,
  spacing: { after: 200 },
  children: [new TextRun({
    text: "תוכן עניינים", font: "David", size: 32, bold: true, rightToLeft: true
  })]
}),
tocEntry("פרק א׳, הגדרות כלליות", 2, { bold: true }),
tocEntry("1. הגדרות יסוד", 2, { indent: 400 }),
tocEntry("פרק ב׳, השירותים", 3, { bold: true }),
new Paragraph({ children: [new PageBreak()] }),
```

---

## קו תחתי (Underline)

```javascript
const { UnderlineType } = require('docx');

// קו תחתי רגיל:
new TextRun({
  text: "נושא: הסכם שירותים",
  font: "David", size: 24, rightToLeft: true,
  underline: { type: UnderlineType.SINGLE }
})

// קו תחתי כפול (לכותרות חשובות):
underline: { type: UnderlineType.DOUBLE }

// סוגים שימושיים: SINGLE, DOUBLE, THICK, DOTTED, DASH, WAVE
```

---

## מספר סקשנים (Multiple Sections)

**שימוש:** כותרות שונות לנספחים, עמוד לרוחב לטבלאות, שוליים שונים.

```javascript
const doc = new Document({
  sections: [
    // סקשן 1, גוף ההסכם
    {
      properties: {
        page: { size: { width: 11906, height: 16838 },
                margin: { top: 1417, right: 1417, bottom: 1417, left: 1417 } },
        bidi: true,
      },
      headers: {
        default: new Header({ children: [new Paragraph({
          bidirectional: true, alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "הסכם שירותים", font: "David", size: 20, bold: true, rightToLeft: true })]
        })] })
      },
      children: [ /* ... */ ]
    },
    // סקשן 2, נספח עם כותרת שונה
    {
      properties: {
        page: { size: { width: 11906, height: 16838 },
                margin: { top: 1417, right: 1417, bottom: 1417, left: 1417 } },
        bidi: true,
      },
      headers: {
        default: new Header({ children: [new Paragraph({
          bidirectional: true, alignment: AlignmentType.START,  // START
          children: [new TextRun({ text: "נספח א׳, לוח תעריפים", font: "David", size: 20, bold: true, rightToLeft: true })]
        })] })
      },
      children: [ /* ... */ ]
    }
  ]
});
```

---

## לוגו/תמונה בכותרת (Letterhead)

```javascript
const { ImageRun } = require('docx');

const logoBuffer = fs.readFileSync('/path/to/logo.png');

headers: {
  default: new Header({
    children: [
      new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [
          new ImageRun({
            data: logoBuffer,
            transformation: { width: 200, height: 60 },  // pixels
            type: "png",
          }),
        ],
      }),
      new Paragraph({
        bidirectional: true, alignment: AlignmentType.CENTER,
        children: [new TextRun({
          text: "משרד עורכי דין ישראלי ושות׳",
          font: "David", size: 20, bold: true, rightToLeft: true
        })],
      }),
    ],
  }),
}
```

**הערה:** תמונה חייבת להיות קובץ אמיתי - לבקש מהמשתמש אם אין.

---

## היפרלינקים

```javascript
const { ExternalHyperlink, UnderlineType } = require('docx');

new Paragraph({
  bidirectional: true,
  children: [
    new TextRun({ text: "ראה: ", font: "David", size: 24, rightToLeft: true }),
    new ExternalHyperlink({
      link: "https://www.nevo.co.il/law_html/law01/073_002.htm",
      children: [new TextRun({
        text: "חוק החוזים באתר נבו",
        font: "David", size: 24, rightToLeft: true,
        color: "0563C1",
        underline: { type: UnderlineType.SINGLE },
      })],
    }),
  ]
})
```

**אזהרות:**
- **לא להשתמש ב-`style: "Hyperlink"`** - מפריע ל-RTL!
- **לא להוסיף `alignment: AlignmentType.RIGHT`** - `bidirectional: true` מספיק

---
