# marcus-law - Marketplace פרטי לפלאג-אינים משפטיים

Repository זה הוא ה-marketplace הפרטי של משרד מרקוס, ומשמש מקור התקנה ועדכון לכל המחשבים שבהם מותקן Claude Code וכן ל-Claude Desktop (Cowork).

## כתובות ה-marketplace

| מקור | כתובת | תפקיד |
|---|---|---|
| **GitHub** | `https://github.com/PointStarIL/skills_and_plugins` | **מקור-אמת** — כאן נדחפים השינויים, וכאן ממוזגים PRs שמפעילים את הסנכרון ל-Claude Desktop (Cowork) |
| **Gitea (פרטי)** | `https://gitea.prod.marcus-law.co.il/skills_and_plugins/marketplace.git` | **mirror** — עותק גיבוי פרטי שמסונכרן אוטומטית מ-GitHub (cron בשרת hetzner) |

> **שים לב — היפוך תפקידים (2026-05-31):** עד היום Gitea היה מקור-האמת ו-GitHub היה ה-mirror.
> כעת ההפך: **GitHub הוא מקור-האמת**. הסיבה: Claude Desktop (Cowork) מסנכרן את ה-marketplace
> רק כש**ממוזג PR ב-GitHub** (auto-sync), ו-push-mirror מ-Gitea לעולם לא יוצר אירוע מיזוג-PR.
> ראה את הסעיף "עדכון ב-Claude Desktop (Cowork)" למטה.

**הוספת marketplace במחשב חדש** (GitHub — עובד גם ב-Claude Desktop GUI):
```
/plugin marketplace add PointStarIL/skills_and_plugins
```

**התקנת הפלאג-אינים** (שם marketplace: `marcus-law`):
```
/plugin install marcus-law-appeal-committee@marcus-law
/plugin install marcus-law-drafting@marcus-law
/plugin install marcus-law-content@marcus-law
/plugin install marcus-law-client-management@marcus-law
```

**עדכון ב-Claude Code (CLI)**:
```
/plugin marketplace update marcus-law
/plugin update
```
(שם ה-marketplace המקומי ב-CLI הוא `marcus-law` — משדה `name` ב-`marketplace.json`. אי-ההתאמה
לשם ה-repo `skills_and_plugins` שנראה ב-directory תקינה ואינה דורשת תיקון.)

**עדכון ב-Claude Desktop (Cowork)** — המנגנון שונה לחלוטין מה-CLI:
- ה-marketplace מסונכרן מ-GitHub. **auto-sync מופעל רק כשממוזג PR ל-repo ב-GitHub**, ולכן
  פרסום שינויים נעשה דרך **branch + PR + merge** ב-GitHub (לא push ישיר ל-main בלבד).
- סנכרון ידני בכל רגע: Customize → Plugins → לבחור את ה-marketplace → ללחוץ **"Update"**.
- דרישת תשתית: **Claude GitHub App** מותקן על `PointStarIL/skills_and_plugins`, ו-"Sync automatically" דלוק.
- הסנכרון עשוי לקחת **עד ~30 דקות**, והשינוי נכנס ב-session הבא או אחרי refresh.
- מקור רשמי: Anthropic Help Center מאמרים #13837440 ("Use plugins in Claude") ו-#13837433
  ("Manage plugins for your organization").

## מבנה ה-repository

```
.
├── .claude-plugin/
│   └── marketplace.json        קטלוג ה-marketplace (רשימת הפלאג-אינים)
├── plugins/                    כל פלאג-אין בתת-תיקייה משלו
│   ├── marcus-law-appeal-committee/   ועדת ערר: טיפול בעררים + כתיבת החלטות
│   │   ├── .claude-plugin/plugin.json
│   │   ├── skills/<skill>/SKILL.md
│   │   ├── agents/
│   │   └── README.md
│   ├── marcus-law-drafting/           ייצור מסמכים (מנוע DOCX, ניקוי, נספחים)
│   ├── marcus-law-content/            מצגות, מאמרים, NotebookLM
│   ├── marcus-law-client-management/  ארגון תיקי לקוח (סיוע משפטי)
│   └── _template-plugin/              תבנית להעתקה כשמוסיפים פלאג-אין חדש
└── README.md
```

## איך מוסיפים פלאג-אין חדש

1. העתק את `plugins/_template-plugin` לתיקייה חדשה תחת `plugins/` בשם הפלאג-אין (kebab-case).
2. ערוך את `plugin.json` (שדה `name` חייב להיות זהה לשם התיקייה).
3. הוסף את הסקיילים תחת `skills/<skill-name>/SKILL.md`.
4. הוסף רשומה חדשה למערך `plugins` בקובץ `.claude-plugin/marketplace.json`, עם `name` ו-`source` יחסי (`./plugins/<plugin-name>`).
5. commit, ופרסם דרך **PR ל-main ב-GitHub** (`git push origin <branch>` ואז מיזוג ה-PR).
   המיזוג מפעיל את ה-auto-sync של Claude Desktop (Cowork); משתמשי Claude Code יקבלו את
   העדכון אחרי `/plugin marketplace update`. ה-mirror ב-Gitea מתעדכן אוטומטית מ-GitHub.

## מנוע DOCX משותף (hebrew-docx-engine)

הסקיל `hebrew-docx-engine` שבחבילת `marcus-law-drafting` הוא **מקור-האמת היחיד**
לעיצוב מסמכי Word בעברית: RTL נכון, פונט David, מספור, שוליים וסגנונות. כל
שינוי עיצוב נעשה ב-`template.docx` שלו וחל על כל המסמכים.

- חבילות `marcus-law-appeal-committee` ו-`marcus-law-client-management` מצהירות תלות
  (`dependencies`) על `marcus-law-drafting`, כך שהמנוע מותקן אוטומטית איתן.
- `clean-lawmate-draft` ו-`edit-legal-docx` (באותה חבילה) משתמשים במנוע ישירות.
- `write-appeal-decision` (חבילת `marcus-law-appeal-committee`) הוא יוצא דופן מכוון: צורת
  החלטת ועדת ערר שונה (פרוזה ללא מספור, שלוש רמות כותרת), ולכן הוא שומר מימוש RTL
  עצמאי משלו ואינו עובר דרך המנוע.

## מנגנון גרסאות ועדכון

קובצי ה-`plugin.json` כאן מגדירים שדה `version` מפורש, ויש **להעלות אותו בכל שינוי** בחבילה
(1.0.1 → 1.1.0 וכו'). אל תגדיר `version` גם ב-`plugin.json` וגם ברשומת ה-marketplace — הערך
ב-`plugin.json` תמיד גובר.

הבדל חשוב בין שני המנגנונים:
- **Claude Desktop (Cowork)** לוקח את **המצב הנוכחי של ה-repo** בכל סנכרון (השוואת commit אחרון
  מול אחרון-שסונכרן), ולכן **לא** מצריך העלאת `version` כדי לקבל שינוי — מה שמפעיל סנכרון הוא
  **מיזוג PR** (או לחיצת "Update").
- **Claude Code (CLI)** מכבד את שדה ה-`version`: אם הוא מוגדר ולא עלה, המשתמש לא יקבל את
  השינוי גם אחרי `marketplace update`. לכן ההקפדה להעלות `version` בכל שינוי נשמרת.
