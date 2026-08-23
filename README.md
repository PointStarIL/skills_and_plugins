# marcus-law - Marketplace פרטי לפלאג-אינים משפטיים

Repository זה הוא ה-marketplace הפרטי של משרד עורכי דין חיים מרכוס, ומשמש מקור התקנה ועדכון לכל המחשבים שבהם מותקן Claude Code וכן ל-Claude Desktop (Cowork).

> **כללי העבודה ב-repo מרוכזים ב-[CLAUDE.md](CLAUDE.md)** — הגשת תיקונים דרך `upload/`, חובת ה-PR
> והמיזוג, והעלאת גרסאות. מסמך זה הוא הפירוט המלא שמאחוריהם.

## כתובת ה-marketplace

**`https://github.com/PointStarIL/skills_and_plugins`** הוא המקור היחיד. כאן נדחפים
השינויים, וכאן ממוזגים ה-PRs שמפעילים את הסנכרון ל-Claude Desktop (Cowork).

**הוספת marketplace במחשב חדש** (עובד גם ב-Claude Desktop GUI):
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
│   │   ├── .claude-plugin/plugin.json  שם, version, description, dependencies
│   │   ├── CHANGELOG.md                תיעוד השינויים בחבילה - חובה בכל שינוי
│   │   ├── skills/<skill>/SKILL.md
│   │   ├── agents/
│   │   └── README.md
│   ├── marcus-law-drafting/           ייצור מסמכים (מנוע DOCX, ניקוי, נספחים)
│   ├── marcus-law-content/            מצגות, מאמרים, NotebookLM
│   ├── marcus-law-client-management/  ארגון תיקי לקוח (סיוע משפטי)
│   ├── marcus-law-privacy/            OCR מקומי והשחרת פרטים מזהים
│   ├── marcus-law-research/           שליפת נוסח חוקים מספר החוקים הפתוח (ויקיטקסט)
│   └── _template-plugin/              תבנית להעתקה כשמוסיפים פלאג-אין חדש
├── scripts/                    watcher ומעבד לתיקיית upload/ (רצים בשרת)
├── upload/                     תיבת-הדואר לתיקונים (התוכן לא נכנס ל-git)
├── CLAUDE.md                   כללי העבודה ב-repo — קריאת חובה לפני שינוי
└── README.md
```

## איך מוסיפים פלאג-אין חדש

1. העתק את `plugins/_template-plugin` לתיקייה חדשה תחת `plugins/` בשם הפלאג-אין (kebab-case).
2. ערוך את `plugin.json` (שדה `name` חייב להיות זהה לשם התיקייה).
3. הוסף את הסקיילים תחת `skills/<skill-name>/SKILL.md`.
4. הוסף רשומה חדשה למערך `plugins` בקובץ `.claude-plugin/marketplace.json`, עם `name` ו-`source` יחסי (`./plugins/<plugin-name>`).
5. commit, ופרסם דרך **PR ל-main ב-GitHub** (`git push origin <branch>` ואז מיזוג ה-PR).
   המיזוג מפעיל את ה-auto-sync של Claude Desktop (Cowork); משתמשי Claude Code יקבלו את
   העדכון אחרי `/plugin marketplace update`.

## איך מגישים תיקון — תיקיית `upload/`

`upload/` היא תיבת-הדואר של ה-repo: **כל תיקון או שינוי מתחיל בכך שמכניסים לשם קובץ**.
הקובץ מתאר מה לתקן, ו-Claude Code קורא אותו, מחיל את התיקון על ה-repo ומפרסם אותו.

### מה מכניסים לתיקייה

| סוג קובץ | מה זה | מה קורה איתו |
|---|---|---|
| `*.patch` / `*.diff` | פלט של `git diff` / `git format-patch` | Claude מחיל אותו על העץ (`git apply`) ובודק שהתוצאה תקינה |
| `*.md` / `*.txt` | תיאור חופשי בעברית: מה הבעיה, איפה, ומה צריך לתקן | Claude מאתר את הקבצים הרלוונטיים ומבצע את התיקון בעצמו |
| `*.plugin` / `*.skill` | ארכיון zip של חבילה/סקיל שלם | **מסלול אוטומטי נפרד** — ראה "מסלול ה-watcher" למטה |

בקובץ טקסט חופשי כדאי לציין, ככל שידוע: **באיזה סקיל או חבילה** מדובר, **מה קורה היום** ומה
היה צריך לקרות, ואם רלוונטי — ציטוט של המשפט או הפסקה שצריך לשנות. אין צורך בפורמט קבוע;
אם משהו לא ברור, Claude ישאל לפני שיבצע.

### מה Claude עושה עם הקובץ

1. קורא את כל הקבצים ב-`upload/` (למעט `.gitkeep` וקבצים מוסתרים).
2. מבין באיזו חבילה וסקיל מדובר, ומחיל את התיקון — patch באמצעות `git apply`, או עריכה ידנית לפי התיאור.
3. **מעלה `version`** ב-`SKILL.md` של הסקיל שהשתנה וב-`plugin.json` של החבילה (ראה "מנגנון גרסאות ועדכון").
4. פותח branch, מבצע commit ו**פותח PR ל-main ב-GitHub** — לא push ישיר ל-main.
5. **ה-PR חייב להיות ממוזג (merge) כדי שהעדכון יגיע למשתמשים.** כל עוד ה-PR פתוח, השינוי לא הופץ
   לאיש: מיזוג ה-PR הוא האירוע שמפעיל את ה-auto-sync של Claude Desktop (Cowork), והוא גם מה שמעדכן
   את `main` שממנו מושכים משתמשי Claude Code ב-`/plugin marketplace update`. תיקון שנשאר ב-branch
   בלבד אינו קיים מבחינת אף מחשב אחר.
6. מדווח מה נעשה, כולל קישור ל-PR, ושואל אם למחוק את קובץ התיקון מ-`upload/`.

> **הכלל בשורה אחת:** קובץ ב-`upload/` ← תיקון ב-branch ← PR ← **merge ל-main** ← הפצה לכל המחשבים.
> בלי המיזוג, שום שלב קודם לא מגיע לאף אחד.

תוכן `upload/` מוחרג ב-`.gitignore` (`upload/*` למעט `.gitkeep`), ולכן קובצי התיקון עצמם
לעולם אינם נכנסים ל-repo — רק התוצאה שלהם.

### מסלול ה-watcher (אוטומטי, לחבילות שלמות)

בשרת רץ `scripts/watch-upload.sh` כ-systemd service, שמזהה קבצים חדשים ב-`upload/` ומריץ עליהם
את `scripts/process-upload.sh`. הוא מטפל **רק** בקבצי `.plugin` ו-`.skill` (ארכיוני zip): מחלץ אותם
לתוך `plugins/<name>/`, מוסיף רשומה ל-`marketplace.json` אם החבילה חדשה, ודוחף commit.
קובצי `.patch` / `.md` / `.txt` נדחים על ידו בהודעת שגיאה ונשארים בתיקייה — וזה בדיוק הרצוי:
הם מיועדים לטיפול של Claude, לא של ה-watcher.

> שים לב: ה-watcher דוחף ישירות (`git push`) ואינו פותח PR. לכן שינוי שנועד להגיע ל-Claude Desktop
> (Cowork) עדיף שיעבור במסלול ה-PR המתואר למעלה.

## מנוע ה-DOCX היחיד (hebrew-docx-engine)

**במערכת יש מנוע DOCX אחד בלבד.** הסקיל `hebrew-docx-engine` שבחבילת `marcus-law-drafting`
הוא מקור-האמת לעיצוב מסמכי Word בעברית: RTL נכון, פונט David, מספור בארבע רמות, שוליים
וסגנונות בשם. כל שינוי עיצוב נעשה ב-`references/template.docx` שלו וחל על כל המסמכים.

```
plugins/marcus-law-drafting/skills/hebrew-docx-engine/
├── scripts/docx_hebrew_engine.py    המנוע
└── references/template.docx         העיצוב (61 סגנונות)
```

- **כל בנייה של DOCX עברי מאפס חייבת לעבור דרכו.** סקיל שחסרה לו יכולת מרחיב את המנוע
  ולא עוקף אותו. ה-API והעקרונות ב-`skills/hebrew-docx-engine/SKILL.md`.
- חבילות `marcus-law-appeal-committee` ו-`marcus-law-client-management` מצהירות תלות
  (`dependencies`) על `marcus-law-drafting`, כך שהמנוע מותקן אוטומטית איתן.
- `edit-legal-docx`, `organize-client-folder`, `extract-appeal-claims` ו-`write-appeal-decision`
  בונים דרכו. **אין מנוע שני ואין חריגים.** `edit-legal-docx` מטפל בעריכת DOCX **קיים**
  ובמבנה המשפטי, ומפנה לכאן לבנייה מאפס.

## מנגנון גרסאות ועדכון

הכללים המלאים ב-[CLAUDE.md § 3](CLAUDE.md). התמצית:

**החבילה היא יחידת ההפצה, לא הסקיל.** Claude Code מושך את החבילה כולה כיחידה אחת לתיקיית
מטמון `~/.claude/plugins/cache/marcus-law/<plugin>/<version>/`, ומשתמש בגרסת הפלאג-אין כ-cache key
שקובע אם קיים עדכון. אין מנגנון להפיץ סקיל בודד מתוך חבילה: תיקנת סקיל אחד מתוך שבעה —
מעלים את גרסת החבילה פעם אחת, וכל שבעת הסקיילים נשלחים יחד.

**הגרסה נפתרת לפי הסדר הזה**, והראשון שמוגדר מנצח: `version` ב-`plugin.json` ← `version` ברשומת
ה-marketplace ← git commit SHA של המקור ← sha256 (למקורות archive) ← `unknown`. **בכל חמש
החבילות מוגדר `version` מפורש ב-`plugin.json`**, ולכן המשתמשים מקבלים שינוי רק כשהמספר עולה.

### נקודת האפס ושער האישור

ב-**2026-08-11** אופסו כל החבילות ל-`1.0.0` וכל הסקיילים ל-`metadata.version: "1.0.0"`,
והחל מאותו תאריך כל שינוי מתועד ב-`plugins/<plugin>/CHANGELOG.md`. **אין העלאת גרסה בלי
רשומה, ואין שינוי מופץ בלי העלאת גרסה.**

העלאת המספר כפופה לשער אישור:

| רמה | דוגמה | מי מאשר |
|---|---|---|
| **PATCH** (הספרה השלישית) | 1.0.0 → 1.0.1 | Claude רשאי לבצע לבד |
| **MINOR** (הספרה האמצעית) | 1.0.1 → 1.1.0 | טעון אישור מפורש ומנומק של המשתמש |
| **MAJOR** (הספרה הראשונה) | 1.1.0 → 2.0.0 | טעון אישור מפורש; לשינוי שובר תאימות בלבד |

PATCH הוא תיקון שאינו משנה מה הסקיל עושה; MINOR הוא יכולת חדשה; MAJOR הוא שבירת תאימות.
בספק — הרמה הנמוכה, ולשאול. הפירוט המלא ב-[CLAUDE.md § 3](CLAUDE.md).

**אל תגדיר `version` גם ב-`plugin.json` וגם ברשומת ה-marketplace** — הערך ב-`plugin.json` תמיד גובר.

הבדל בין שני לקוחות הקצה:
- **Claude Desktop (Cowork)** לוקח את **המצב הנוכחי של ה-repo** בכל סנכרון, ולכן לא מצריך העלאת
  `version` כדי לקבל שינוי — מה שמפעיל סנכרון הוא **מיזוג PR** (או לחיצת "Update").
- **Claude Code (CLI)** מכבד את שדה ה-`version`: אם הוא מוגדר ולא עלה, המשתמש לא יקבל את
  השינוי גם אחרי `marketplace update`.

### גרסת הסקיל (`SKILL.md`)

`version` **אינו שדה מוכר** ב-frontmatter של SKILL.md, לא אצל Claude Code ולא במפרט
[Agent Skills](https://agentskills.io) (שמתיר `name`, `description`, `license`, `compatibility`,
`metadata`, `allowed-tools`). לכן גרסת הסקיל נשמרת תחת `metadata`, שהוא המקום שהמפרט ייעד
לנתונים פרטיים:

```yaml
---
name: extract-appeal-claims
description: "..."
metadata:
  version: "1.5.0"
---
```

הערך הזה הוא **מעקב היסטורי לבני אדם בלבד** ואינו משפיע על הפצה. הוא עצמאי מגרסת החבילה
ואינו חייב להיות זהה לה: תיקון בסקיל אחד מעלה את המונה שלו ואת מונה החבילה, ושאר הסקיילים
באותה חבילה נשארים במקומם.

קובצי `CHANGELOG.md` שנמצאים בתוך תיקיות סקיל הם **ארכיון** מלפני נקודת האפס ואינם מתעדכנים.
