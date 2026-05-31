#!/usr/bin/env node
/**
 * create-decision.js - תבנית למסמך החלטת ועדת ערר לתכנון ובניה
 *
 * שימוש: העתק לתיקיית העבודה, ערוך את CONTENT, הרץ עם node.
 *
 * מבוסס על הטמפלט הרשמי של ועדת הערר.
 * ערכים ייחודיים: שוליים 1797 DXA, גוף 13pt, כותרות פרקים 13pt bold+underline,
 * כותרת מוסדית 14pt center, סעיפים ממוספרים 14pt David.
 *
 * v1.0
 */

const fs = require('fs');
const { Document, Packer, Paragraph, TextRun, Footer,
        AlignmentType, PageNumber, LevelFormat,
        LineRuleType, UnderlineType } = require('docx');

// ═══════════════════════════════════════════════
// CONFIGURATION - הגדרות ספציפיות להחלטת ועדת ערר
// ═══════════════════════════════════════════════
const FONT_CS = "David";
const FONT_ASCII = "Times New Roman";
const BODY_SIZE = 26;              // 13pt - גוף הטקסט
const HEADING3_SIZE = 28;          // 14pt - כותרת מוסדית
const LIST_SIZE = 28;              // 14pt - סעיפים ממוספרים
const QUOTE_LINE_SPACING = 276;    // מרווח 1.15 לציטוטים
const BODY_LINE_SPACING = 360;     // מרווח 1.5 לגוף

// שוליים - רחבים יותר מהסטנדרט המשפטי!
const MARGINS = {
  top: 1440,     // ~2.54 ס"מ
  right: 1797,   // ~3.17 ס"מ
  bottom: 1077,  // ~1.9 ס"מ
  left: 1797,    // ~3.17 ס"מ
  header: 709,
  footer: 510
};

const OUTPUT_FILE = "decision.docx";

// ═══════════════════════════════════════════════
// HELPERS - פונקציות עזר
// ═══════════════════════════════════════════════

// TextRun לגוף הטקסט (Times New Roman ASCII + David CS)
const bodyRun = (text, opts = {}) => new TextRun({
  text,
  font: { ascii: FONT_ASCII, hAnsi: FONT_ASCII, cs: FONT_CS },
  size: opts.size || BODY_SIZE,
  rightToLeft: true,
  color: "000000",
  ...opts
});

// TextRun ב-David בלבד (לסעיפים ממוספרים)
const davidRun = (text, opts = {}) => new TextRun({
  text,
  font: FONT_CS,
  size: opts.size || LIST_SIZE,
  rightToLeft: true,
  ...opts
});

// Paragraph רגיל - Normal
const normalPara = (children, opts = {}) => new Paragraph({
  bidirectional: true,
  alignment: opts.alignment || AlignmentType.BOTH,
  spacing: {
    before: 120, after: 120,
    line: BODY_LINE_SPACING, lineRule: LineRuleType.AUTO
  },
  indent: { left: -454 },
  children: Array.isArray(children) ? children : [children],
  ...opts
});

// Heading 2 - כותרת פרק (bold + underline, אותו גודל כמו גוף!)
const heading2 = (text) => new Paragraph({
  bidirectional: true,
  alignment: AlignmentType.BOTH,
  spacing: {
    before: 160, after: 120,
    line: BODY_LINE_SPACING, lineRule: LineRuleType.AUTO
  },
  indent: { left: -567 },
  keepNext: true,
  children: [new TextRun({
    text,
    font: { ascii: FONT_ASCII, hAnsi: FONT_ASCII, cs: FONT_CS },
    size: BODY_SIZE,           // 13pt - אותו גודל כמו Normal!
    bold: true,
    rightToLeft: true,
    underline: { type: UnderlineType.SINGLE }
  })]
});

// Heading 3 - כותרת מוסדית ממורכזת (עמוד ראשון)
const heading3 = (text) => new Paragraph({
  bidirectional: true,
  alignment: AlignmentType.CENTER,
  spacing: { after: 0 },
  children: [new TextRun({
    text,
    font: { ascii: FONT_ASCII, hAnsi: FONT_ASCII, cs: FONT_CS },
    size: HEADING3_SIZE,       // 14pt
    bold: true,
    rightToLeft: true
  })]
});

// Quote - בלוק ציטוט (bold, מרווח צפוף, מוזח)
const quote = (text) => new Paragraph({
  bidirectional: true,
  alignment: AlignmentType.BOTH,
  spacing: {
    before: 0, after: 0,
    line: QUOTE_LINE_SPACING, lineRule: LineRuleType.AUTO  // 1.15
  },
  indent: { left: 680, right: 170 },
  children: [new TextRun({
    text,
    font: { ascii: FONT_ASCII, hAnsi: FONT_ASCII, cs: FONT_CS },
    size: BODY_SIZE,
    bold: true,
    rightToLeft: true
  })]
});

// List Paragraph - סעיף ממוספר (David 14pt)
const listPara = (text, numRef = "decision-clauses", level = 0) => new Paragraph({
  bidirectional: true,
  alignment: AlignmentType.BOTH,
  spacing: {
    before: 120, after: 0,
    line: BODY_LINE_SPACING, lineRule: LineRuleType.AUTO
  },
  numbering: { reference: numRef, level },
  children: [davidRun(text)]
});

// שורה ריקה
const spacer = () => normalPara([bodyRun("")]);

// ═══════════════════════════════════════════════
// CONTENT - ערוך כאן את תוכן ההחלטה
// ═══════════════════════════════════════════════

const CONTENT = [
  // --- בלוק כותרת מוסדי ---
  heading3("מדינת ישראל"),
  heading3("ועדת ערר לתכנון ובניה"),
  heading3("מחוז ירושלים"),
  heading3(""),
  heading3("ערר XXX/XX"),
  heading3(""),
  heading3("הרכב הוועדה:"),
  heading3("יו\"ר: [שם היו\"ר]"),
  heading3("חברים: [שם חבר 1], [שם חבר 2]"),
  heading3(""),
  heading3("העוררים: [שם] ע\"י ב\"כ עו\"ד [שם]"),
  heading3("המשיבות: [שם] ע\"י ב\"כ עו\"ד [שם]"),
  heading3(""),
  heading3("החלטה"),
  spacer(),

  // --- רקע ---
  heading2("רקע"),
  listPara("לפנינו ערר על החלטת הוועדה המקומית לתכנון ובניה [שם] מיום [תאריך] לאשר/לדחות את הבקשה להיתר בניה מספר [מספר]."),
  listPara("[תיאור הנכס והבקשה...]"),
  listPara("[פירוט ההליכים...]"),

  // --- תכנית ---
  heading2("התכנית החלות על המקרקעין"),
  listPara("[תיאור התכנית הרלוונטית...]"),

  // --- טענות ---
  heading2("תמצית טענות הצדדים"),

  heading2("טענות העוררים"),
  listPara("העוררים טוענים כי [טענה ראשונה...]"),
  listPara("לטענתם, [טענה שנייה...]"),
  listPara("עוד ציינו כי [טענה שלישית...]"),

  heading2("תגובת המשיבות"),
  listPara("הוועדה המקומית הציגה את עמדתה באופן מפורט. הטענה המרכזית הינה כי [תגובה...]"),
  listPara("הוועדה המקומית הבהירה כי [תגובה נוספת...]"),

  // --- דיון ---
  heading2("דיון והכרעה"),
  listPara("לאחר שבחנו את טענות הצדדים ועיון במסמכים שהוגשו, הגענו לכלל מסקנה כי [מסקנה]."),
  listPara("[ניתוח...]"),

  // ציטוט מפסיקה
  listPara("נפנה בעניין זה להחלטת ועדת הערר בערר [מספר]:"),
  quote("[ציטוט ארוך מפסיקה או מהחלטה מרכזת...]"),

  listPara("[המשך ניתוח...]"),
  listPara("אם כך, [מסקנת ביניים...]"),

  // --- סוף דבר ---
  heading2("סוף דבר"),
  listPara("לאור כל האמור לעיל, הערר מתקבל/נדחה."),
  listPara("[הוראות אופרטיביות...]"),
  normalPara([bodyRun("בנסיבות העניין, אין צו להוצאות.")]),

  // --- חתימה ---
  spacer(),
  normalPara([bodyRun(
    "ניתנה פה אחד היום, \u200F[תאריך עברי], \u200F[תאריך לועזי].",
    { bold: true }
  )]),
  spacer(),
  normalPara([bodyRun("[שם היו\"ר], יו\"ר ועדת הערר")]),
  normalPara([bodyRun("[שם], מזכירת ועדת הערר")]),
];

// ═══════════════════════════════════════════════
// DOCUMENT GENERATION
// ═══════════════════════════════════════════════

const doc = new Document({
  styles: {
    default: {
      document: {
        run: {
          font: { ascii: FONT_ASCII, hAnsi: FONT_ASCII, cs: FONT_CS },
          size: BODY_SIZE,
          rightToLeft: true
        },
        paragraph: { bidirectional: true, alignment: AlignmentType.BOTH }
      }
    }
  },
  numbering: {
    config: [
      {
        // מספור עשרוני רציף (1. 2. 3. ...)
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
              run: { font: FONT_CS, size: LIST_SIZE }
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
        // מספור עברי - לסעיפי סיכום בדחייה (א. ב. ג.)
        reference: "decision-hebrew",
        levels: [{
          level: 0,
          format: LevelFormat.HEBREW_1,
          text: "%1.",
          alignment: AlignmentType.CENTER,
          suffix: "tab",
          style: {
            paragraph: { indent: { left: 1080, hanging: 360 } },
            run: { font: FONT_CS }
          }
        }]
      }
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },
        margin: MARGINS
      },
      bidi: true,
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          bidirectional: true,
          alignment: AlignmentType.CENTER,
          children: [
            bodyRun("עמוד "),
            new TextRun({ children: [PageNumber.CURRENT], font: FONT_CS, size: BODY_SIZE, rightToLeft: true }),
            bodyRun(" מתוך "),
            new TextRun({ children: [PageNumber.TOTAL_PAGES], font: FONT_CS, size: BODY_SIZE, rightToLeft: true }),
          ]
        })]
      })
    },
    children: CONTENT
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(OUTPUT_FILE, buffer);
  console.log(`✅ ${OUTPUT_FILE} created successfully`);
  console.log(`   Font: ${FONT_CS} (CS) / ${FONT_ASCII} (ASCII)`);
  console.log(`   Body: ${BODY_SIZE/2}pt | List: ${LIST_SIZE/2}pt | Heading3: ${HEADING3_SIZE/2}pt`);
  console.log(`   Margins: ${MARGINS.right} DXA (~3.17cm)`);
  console.log(`   Line spacing: ${BODY_LINE_SPACING} (body) / ${QUOTE_LINE_SPACING} (quotes)`);
  console.log(`   Size: ${(buffer.length / 1024).toFixed(1)} KB`);
});
