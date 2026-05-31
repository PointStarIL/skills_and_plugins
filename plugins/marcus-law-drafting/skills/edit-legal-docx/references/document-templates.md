# תבניות מסמכים משפטיים

קובץ עיון זה מכיל את התבניות המלאות של סוגי המסמכים. נטען לפי צורך מ-SKILL.md.

## תוכן עניינים

- תבניות מסמכים - Document Templates

## תבניות מסמכים - Document Templates

### תבנית 1: כתב טענות (בקשה, תביעה, הגנה, ערעור)

```javascript
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        AlignmentType, LevelFormat, BorderStyle, WidthType } = require('docx');

const PAGE_WIDTH = 11906;
const MARGINS = { top: 1134, right: 1134, bottom: 1134, left: 1134 };
const CONTENT_WIDTH = PAGE_WIDTH - MARGINS.left - MARGINS.right;

const noBorder = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };

// Header בית משפט, טבלה עם שם בית המשפט (ימין) ומספר תיק (שמאל)
function courtHeader(courtName, caseNumber) {
  return new Table({
    width: { size: CONTENT_WIDTH, type: WidthType.DXA },
    columnWidths: [CONTENT_WIDTH / 2, CONTENT_WIDTH / 2],
    visuallyRightToLeft: true,
    rows: [
      new TableRow({
        children: [
          new TableCell({
            width: { size: CONTENT_WIDTH / 2, type: WidthType.DXA },
            borders: noBorders,
            children: [new Paragraph({
              bidirectional: true, alignment: AlignmentType.START,
              children: [new TextRun({ text: courtName, bold: true, font: "David", size: 26, rightToLeft: true })]
            })]
          }),
          new TableCell({
            width: { size: CONTENT_WIDTH / 2, type: WidthType.DXA },
            borders: noBorders,
            children: [new Paragraph({
              bidirectional: true, alignment: AlignmentType.END,
              children: [new TextRun({ text: caseNumber, bold: true, font: "David", size: 26, rightToLeft: true })]
            })]
          })
        ]
      })
    ]
  });
}

// כותרת ראשית ממורכזת עם קו תחתון
function mainTitle(text) {
  return new Paragraph({
    bidirectional: true, alignment: AlignmentType.CENTER,
    spacing: { before: 300, after: 300 },
    children: [new TextRun({ text, bold: true, font: "David", size: 28, rightToLeft: true, underline: {} })]
  });
}

// כותרת משנה מיושרת לימין עם קו תחתון
function subHeading(text) {
  return new Paragraph({
    bidirectional: true, alignment: AlignmentType.START,
    spacing: { before: 240, after: 120 },
    children: [new TextRun({ text, bold: true, font: "David", size: 24, rightToLeft: true, underline: {} })]
  });
}

// שימוש:
const doc = new Document({
  numbering: {
    config: [{
      reference: "legal-clauses",
      levels: [{
        level: 0, format: LevelFormat.DECIMAL, text: "%1.",
        alignment: AlignmentType.START, suffix: "tab",
        style: { paragraph: { indent: { left: 360, hanging: 360 } } }
      }]
    }]
  },
  sections: [{
    properties: {
      page: { size: { width: PAGE_WIDTH, height: 16838 }, margin: MARGINS },
      bidi: true
    },
    children: [
      courtHeader("בית המשפט המחוזי בתל אביב", "ת\"א 12345-01-26"),
      mainTitle("כתב תביעה"),
      // ... פרטי צדדים, סעיפים, חתימה
    ]
  }]
});
```

### תבנית 2: מכתב התראה

```javascript
// מכתב התראה, ללא header בית משפט, עם פרטי משרד

function letterHeader(firmName, address, phone, email) {
  return [
    new Paragraph({
      bidirectional: true, alignment: AlignmentType.START,
      children: [new TextRun({ text: firmName, bold: true, font: "David", size: 28, rightToLeft: true })]
    }),
    new Paragraph({
      bidirectional: true, alignment: AlignmentType.START,
      children: [new TextRun({ text: address, font: "David", size: 22, rightToLeft: true })]
    }),
    new Paragraph({
      bidirectional: true, alignment: AlignmentType.START,
      spacing: { after: 300 },
      children: [new TextRun({ text: `טל': ${phone} | ${email}`, font: "David", size: 22, rightToLeft: true })]
    }),
  ];
}

function subjectLine(text) {
  return new Paragraph({
    bidirectional: true, alignment: AlignmentType.CENTER,
    spacing: { before: 200, after: 200 },
    children: [
      new TextRun({ text: "הנדון: ", bold: true, font: "David", size: 24, rightToLeft: true }),
      new TextRun({ text, bold: true, font: "David", size: 24, rightToLeft: true, underline: {} })
    ]
  });
}

// שימוש:
sections: [{
  properties: { page: { ... }, bidi: true },
  children: [
    ...letterHeader("משרד עו\"ד כהן ושות'", "רח' הרצל 1, תל אביב", "03-1234567", "office@cohen-law.co.il"),
    new Paragraph({
      bidirectional: true, alignment: AlignmentType.START,
      children: [new TextRun({ text: "תאריך: 10.2.2026", font: "David", size: 24, rightToLeft: true })]
    }),
    new Paragraph({
      bidirectional: true, alignment: AlignmentType.START,
      spacing: { before: 200 },
      children: [new TextRun({ text: "לכבוד: [שם הנמען]", font: "David", size: 24, rightToLeft: true })]
    }),
    subjectLine("התראה בטרם נקיטת הליכים משפטיים"),
    // ... גוף המכתב
  ]
}]
```

### תבנית 3: הסכם/חוזה

```javascript
// הסכם, הואילים, צדדים, חתימות בשני טורים

function contractTitle(text) {
  return new Paragraph({
    bidirectional: true, alignment: AlignmentType.CENTER,
    spacing: { after: 300 },
    children: [new TextRun({ text, bold: true, font: "David", size: 32, rightToLeft: true })]
  });
}

function partyClause(label, name, id, address, alias) {
  return new Paragraph({
    bidirectional: true, alignment: AlignmentType.BOTH,
    spacing: { after: 120 },
    children: [
      new TextRun({ text: `${label}: `, bold: true, font: "David", size: 24, rightToLeft: true }),
      new TextRun({ text: `${name}, ח.פ./ת.ז. ${id}, מ${address} (להלן: "`, font: "David", size: 24, rightToLeft: true }),
      new TextRun({ text: alias, bold: true, font: "David", size: 24, rightToLeft: true }),
      new TextRun({ text: '")', font: "David", size: 24, rightToLeft: true }),
    ]
  });
}

function signatureTable() {
  return new Table({
    width: { size: CONTENT_WIDTH, type: WidthType.DXA },
    columnWidths: [CONTENT_WIDTH / 2, CONTENT_WIDTH / 2],
    visuallyRightToLeft: true,
    rows: [
      new TableRow({
        children: [
          new TableCell({
            borders: noBorders,
            children: [
              new Paragraph({ bidirectional: true, alignment: AlignmentType.CENTER,
                children: [new TextRun({ text: "_________________", font: "David", size: 24, rightToLeft: true })] }),
              new Paragraph({ bidirectional: true, alignment: AlignmentType.CENTER,
                children: [new TextRun({ text: "צד א'", font: "David", size: 24, rightToLeft: true })] })
            ]
          }),
          new TableCell({
            borders: noBorders,
            children: [
              new Paragraph({ bidirectional: true, alignment: AlignmentType.CENTER,
                children: [new TextRun({ text: "_________________", font: "David", size: 24, rightToLeft: true })] }),
              new Paragraph({ bidirectional: true, alignment: AlignmentType.CENTER,
                children: [new TextRun({ text: "צד ב'", font: "David", size: 24, rightToLeft: true })] })
            ]
          })
        ]
      })
    ]
  });
}

// שימוש:
sections: [{
  properties: { page: { ... }, bidi: true },
  children: [
    contractTitle("הסכם שירותים"),
    new Paragraph({
      bidirectional: true, alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "נערך ונחתם בתל אביב ביום __________", font: "David", size: 24, rightToLeft: true })]
    }),
    partyClause("מצד אחד", "[שם]", "[מספר]", "[כתובת]", "המזמין"),
    partyClause("מצד שני", "[שם]", "[מספר]", "[כתובת]", "הספק"),
    // הואילים...
    // סעיפים...
    new Paragraph({
      bidirectional: true, alignment: AlignmentType.CENTER,
      spacing: { before: 400, after: 300 },
      children: [new TextRun({ text: "ולראיה באו הצדדים על החתום:", bold: true, font: "David", size: 24, rightToLeft: true })]
    }),
    signatureTable()
  ]
}]
```

### תבנית 4: החלטת ועדת ערר לתכנון ובניה

מסמך ההחלטה של ועדת הערר שונה מכתבי טענות רגילים - יש לו עמוד ראשון מוסדי ממורכז, שוליים רחבים יותר, ומערכת סגנונות ייחודית. הערכים נלקחו מהטמפלט הרשמי של ועדת הערר.

**5 סגנונות פעילים בלבד:** Normal, Heading 2, Heading 3, List Paragraph, Quote. כל שאר הסגנונות מוסתרים.

#### הגדרות עמוד - שונות מהסטנדרט!

```javascript
// שוליים רחבים יותר מכתבי טענות רגילים (~3.17 ס"מ מהצדדים)
const DECISION_MARGINS = {
  top: 1440,     // ~2.54 ס"מ
  right: 1797,   // ~3.17 ס"מ, לא 2.5 ס"מ!
  bottom: 1077,  // ~1.9 ס"מ
  left: 1797,    // ~3.17 ס"מ, לא 2.5 ס"מ!
  header: 709,
  footer: 510
};
const DECISION_CONTENT_WIDTH = 11906 - 1797 - 1797; // = 8312 DXA
```

#### Normal - גוף הטקסט

```javascript
// שונה מברירות המחדל הרגילות (David 12pt):
// פונט CS: David, פונט ASCII: Times New Roman, גודל: 13pt
const decisionNormalRun = (text, opts = {}) => new TextRun({
  text,
  font: { ascii: "Times New Roman", hAnsi: "Times New Roman", cs: "David" },
  size: 26,              // 13pt, לא 12pt!
  rightToLeft: true,
  color: "000000",
  ...opts
});

const decisionParagraph = (children, opts = {}) => new Paragraph({
  bidirectional: true,
  alignment: AlignmentType.BOTH,
  spacing: { before: 120, after: 120, line: 360, lineRule: LineRuleType.AUTO }, // מרווח 1.5
  indent: { left: -454 },
  children,
  ...opts
});
```

#### Heading 2 - כותרות פרקים

כותרות הפרקים הן **באותו גודל כמו גוף הטקסט** (David 13pt). הן מובדלות אך ורק ע"י Bold + קו תחתי. אין שינוי גודל! זהו מאפיין ייחודי למסמכי ועדת הערר.

```javascript
function decisionHeading2(text) {
  return new Paragraph({
    bidirectional: true,
    alignment: AlignmentType.BOTH,
    spacing: { before: 160, after: 120, line: 360, lineRule: LineRuleType.AUTO },
    indent: { left: -567 },
    keepNext: true,
    children: [new TextRun({
      text,
      font: { ascii: "Times New Roman", hAnsi: "Times New Roman", cs: "David" },
      size: 26,            // 13pt, אותו גודל כמו Normal!
      bold: true,
      rightToLeft: true,
      underline: { type: UnderlineType.SINGLE }  // ← קו תחתי!
    })]
  });
}
```

#### Heading 3 - כותרת מוסדית (עמוד ראשון)

סגנון עצמאי לבלוק הכותרת: "מדינת ישראל", "ועדת ערר לתכנון ובניה", מחוז, מספר תיק, הרכב, צדדים, "החלטה".

```javascript
function decisionHeading3(text) {
  return new Paragraph({
    bidirectional: true,
    alignment: AlignmentType.CENTER,  // ← ממורכז!
    spacing: { after: 0 },
    children: [new TextRun({
      text,
      font: { ascii: "Times New Roman", hAnsi: "Times New Roman", cs: "David" },
      size: 28,            // 14pt CS, גדול מגוף הטקסט
      bold: true,
      rightToLeft: true
    })]
  });
}
```

#### Quote - בלוק ציטוט

ציטוטים מופיעים כ-bold, עם מרווח שורות צפוף יותר (1.15 במקום 1.5) והזחה מימין.

```javascript
function decisionQuote(text) {
  return new Paragraph({
    bidirectional: true,
    alignment: AlignmentType.BOTH,
    spacing: { before: 0, after: 0, line: 276, lineRule: LineRuleType.AUTO }, // 1.15
    indent: { left: 680, right: 170 },
    children: [new TextRun({
      text,
      font: { ascii: "Times New Roman", hAnsi: "Times New Roman", cs: "David" },
      size: 26,
      bold: true,          // ← ציטוטים הם bold!
      rightToLeft: true
    })]
  });
}
```

#### מספור סעיפים

```javascript
// מספור עשרוני רציף לאורך כל המסמך (לא מתאפס בין פרקים)
numbering: {
  config: [{
    reference: "decision-clauses",
    levels: [
      {
        level: 0,
        format: LevelFormat.DECIMAL,
        text: "%1.",
        alignment: AlignmentType.START,
        suffix: "tab",
        style: {
          paragraph: { indent: { left: -123, hanging: 360 } },
          run: { font: "David", size: 28 }  // 14pt בסעיפים ממוספרים
        }
      },
      {
        level: 1,
        format: LevelFormat.LOWER_LETTER,
        text: "%2.",
        alignment: AlignmentType.START,
        suffix: "tab",
        style: { paragraph: { indent: { left: 597, hanging: 360 } } }
      }
    ]
  },
  {
    // מספור עברי, לסעיפי סיכום בדחייה בלבד (א. ב. ג.)
    reference: "decision-hebrew",
    levels: [{
      level: 0,
      format: LevelFormat.HEBREW_1,
      text: "%1.",
      alignment: AlignmentType.CENTER,
      suffix: "tab",
      style: {
        paragraph: { indent: { left: 1080, hanging: 360 } },
        run: { font: "David" }
      }
    }]
  }]
}
```

#### List Paragraph - סעיף ממוספר

```javascript
function decisionListParagraph(text, numRef = "decision-clauses", level = 0) {
  return new Paragraph({
    bidirectional: true,
    alignment: AlignmentType.BOTH,
    spacing: { before: 120, after: 0, line: 360, lineRule: LineRuleType.AUTO },
    numbering: { reference: numRef, level },
    children: [new TextRun({
      text,
      font: "David",       // ← הכל David (לא Times New Roman)
      size: 28,             // 14pt, גדול מ-Normal!
      rightToLeft: true
    })]
  });
}
```

#### Footer

```javascript
footers: {
  default: new Footer({
    children: [new Paragraph({
      bidirectional: true,
      alignment: AlignmentType.CENTER,
      children: [
        decisionNormalRun("עמוד "),
        new TextRun({ children: [PageNumber.CURRENT], font: "David", size: 26, rightToLeft: true }),
        decisionNormalRun(" מתוך "),
        new TextRun({ children: [PageNumber.TOTAL_PAGES], font: "David", size: 26, rightToLeft: true }),
      ]
    })]
  })
}
```

#### סדר הפסקאות במסמך

```javascript
sections: [{
  properties: {
    page: { size: { width: 11906, height: 16838 }, margin: DECISION_MARGINS },
    bidi: true,
  },
  footers: { /* כנ"ל */ },
  children: [
    // --- בלוק כותרת מוסדי (Heading 3, ממורכז) ---
    decisionHeading3("מדינת ישראל"),
    decisionHeading3("ועדת ערר לתכנון ובניה"),
    decisionHeading3("מחוז ירושלים"),
    decisionHeading3(""),
    decisionHeading3("ערר XXX/XX"),
    decisionHeading3(""),
    decisionHeading3("הרכב הוועדה:"),
    decisionHeading3("יו\"ר: [שם]"),
    decisionHeading3("חברים: [שם], [שם]"),
    decisionHeading3(""),
    decisionHeading3("העוררים: [שם] ע\"י ב\"כ עו\"ד [שם]"),
    decisionHeading3("המשיבות: [שם] ע\"י ב\"כ עו\"ד [שם]"),
    decisionHeading3(""),
    decisionHeading3("החלטה"),
    decisionParagraph([]),  // שורה ריקה

    // --- רקע (Heading 2 + List Paragraph) ---
    decisionHeading2("רקע"),
    decisionListParagraph("[סעיף רקע ראשון...]"),
    decisionListParagraph("[סעיף רקע שני...]"),

    // --- תכנית (אם רלוונטי) ---
    decisionHeading2("התכנית החלות על המקרקעין"),
    decisionListParagraph("[תיאור התכנית...]"),

    // --- טענות ---
    decisionHeading2("תמצית טענות הצדדים"),
    decisionHeading2("טענות העוררים"),
    decisionListParagraph("[טענה...]"),      // המספור ממשיך!
    decisionHeading2("תגובת המשיבות"),
    decisionListParagraph("[תגובה...]"),     // המספור ממשיך!

    // --- דיון ---
    decisionHeading2("דיון והכרעה"),
    decisionListParagraph("[ניתוח...]"),     // המספור ממשיך!
    decisionQuote("[ציטוט מפסיקה...]"),      // בלוק ציטוט
    decisionListParagraph("[המשך ניתוח...]"),

    // --- סוף דבר ---
    decisionHeading2("סוף דבר"),             // או "סיכום" בדחייה
    decisionListParagraph("[מסקנה...]"),

    // --- חתימה ---
    decisionParagraph([]),  // שורה ריקה
    decisionParagraph([decisionNormalRun(
      "ניתנה פה אחד היום, ‏[תאריך עברי], ‏[תאריך לועזי].",
      { bold: true }
    )]),
  ]
}]
```

#### רשימת בדיקה - החלטת ועדת ערר

```
שוליים 1797 DXA (לא 1417!) ימין+שמאל, 1440 עליון, 1077 תחתון
Section bidi: true
פונט CS: David, פונט ASCII: Times New Roman
גודל גוף: 13pt (26 half-points), לא 12pt!
מרווח שורות גוף: 1.5 (360, auto)
כותרות פרקים (H2): bold + קו תחתי, אותו גודל 13pt, אין שינוי גודל!
כותרת מוסדית (H3): center, David 14pt CS, bold
ציטוטים (Quote): bold, מרווח 1.15 (276), הזחה 680/170
סעיפים ממוספרים (List Paragraph): David 14pt, decimal רציף
מספור עברי (א. ב. ג.) בסעיפי סיכום של דחייה בלבד
Footer: "עמוד X מתוך Y" ממורכז
מספור רציף לאורך כל המסמך, לא מתאפס בין פרקים
```

---
