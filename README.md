# marcus-law - Marketplace פרטי לפלאג-אינים משפטיים

Repository זה הוא ה-marketplace הפרטי של משרד מרקוס. הוא מתארח בשרת Gitea הפרטי ומשמש מקור התקנה ועדכון יחיד לכל המחשבים שבהם מותקן Claude Code.

## כתובות ה-marketplace

| מקור | כתובת |
|---|---|
| **Gitea (מקור-אמת)** | `https://gitea.prod.marcus-law.co.il/skills_and_plugins/marketplace.git` |
| **GitHub (mirror)** | `https://github.com/PointStarIL/skills_and_plugins` |

**הוספת marketplace במחשב חדש** (GitHub — עובד גם ב-Claude Desktop GUI):
```
/plugin marketplace add PointStarIL/skills_and_plugins
```

**התקנת הפלאג-אינים** (שם marketplace: `marcus-law`):
```
/plugin install marcus-law-appeals@marcus-law
/plugin install marcus-law-decisions@marcus-law
/plugin install marcus-law-content@marcus-law
/plugin install marcus-law-client-management@marcus-law
/plugin install marcus-law-drafting@marcus-law
```

**עדכון** (בכל מחשב):
```
/plugin marketplace update
/plugin update
```

## מבנה ה-repository

```
.
├── .claude-plugin/
│   └── marketplace.json        קטלוג ה-marketplace (רשימת הפלאג-אינים)
├── plugins/                    כל פלאג-אין בתת-תיקייה משלו
│   ├── appeal-decision-writer/
│   │   ├── .claude-plugin/plugin.json
│   │   ├── skills/...
│   │   └── README.md
│   ├── appeal-claims-extractor/
│   │   └── ...
│   └── _template-plugin/        תבנית להעתקה כשמוסיפים פלאג-אין חדש
└── README.md
```

## איך מוסיפים פלאג-אין חדש

1. העתק את `plugins/_template-plugin` לתיקייה חדשה תחת `plugins/` בשם הפלאג-אין (kebab-case).
2. ערוך את `plugin.json` (שדה `name` חייב להיות זהה לשם התיקייה).
3. הוסף את הסקיילים תחת `skills/<skill-name>/SKILL.md`.
4. הוסף רשומה חדשה למערך `plugins` בקובץ `.claude-plugin/marketplace.json`, עם `name` ו-`source` יחסי (`./plugins/<plugin-name>`).
5. commit ו-push לשרת. מרגע זה כל מחשב שמושך עדכון יקבל את הפלאג-אין החדש.

## מנוע DOCX משותף (docx-hebrew-engine)

הסקיל `docx-hebrew-engine` שבחבילת `marcus-law-drafting` הוא **מקור-האמת היחיד**
לעיצוב מסמכי Word בעברית: RTL נכון, פונט David, מספור, שוליים וסגנונות. כל
שינוי עיצוב נעשה ב-`template.docx` שלו וחל על כל המסמכים.

- חבילות `marcus-law-appeals` ו-`marcus-law-client-management` מצהירות תלות
  (`dependencies`) על `marcus-law-drafting`, כך שהמנוע מותקן אוטומטית איתן.
- `lawmate-cleaner` ו-`legal-docx` (באותה חבילה) משתמשים במנוע ישירות.
- `appeal-decision-writer` (חבילת decisions) הוא יוצא דופן מכוון: צורת החלטת
  ועדת ערר שונה (פרוזה ללא מספור, שלוש רמות כותרת), ולכן הוא שומר מימוש RTL
  עצמאי משלו ואינו עובר דרך המנוע.

## מנגנון גרסאות ועדכון

בקבצי ה-`plugin.json` כאן **לא** מוגדר שדה `version` בכוונה. כך כל commit חדש נחשב אוטומטית לגרסה חדשה, וכל push מפיץ עדכון. זו ההגדרה הפשוטה ביותר לעבודה שוטפת.

אם בעתיד תרצה שליטה בגרסאות (לשחרר עדכון רק כשאתה מחליט), הוסף שדה `"version": "1.0.0"` ל-`plugin.json` של הפלאג-אין, ובכל שחרור העלה את המספר (1.0.1, 1.1.0 וכו'). חשוב: אל תגדיר `version` גם ב-`plugin.json` וגם ברשומת ה-marketplace, כי הערך ב-`plugin.json` תמיד גובר.
