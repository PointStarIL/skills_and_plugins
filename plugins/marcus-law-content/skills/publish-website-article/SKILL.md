---
name: publish-website-article
description: "מנהל את כל תהליך המאמר לאתר marcus-law.co.il, מבחירת המקור והניסוח ועד העלאה ל-Drive, מעקב אחרי סדנת n8n ואימות באתר החי. הפעל כאשר: 'מאמר לאתר ותפרסם', 'תפרסם מאמר', 'תעלה מאמר לאתר', 'מאמר מפסק דין מהמסד'."
metadata:
  version: "1.0.0"
---

# פרסום מאמר באתר marcus-law.co.il, מקצה לקצה

הסקיל הזה עוטף את `write-website-article` (ניסוח בלבד) ומוסיף את ההעלאה, המעקב והאימות. ללא מקף ארוך בשום טקסט.

## המסלול בקצרה

קובץ MD בתיקיית ה-Drive "מאמרים חדשים" ← סדנת n8n "Article Publisher - Drive to Website" (ID `MjSYn6FSge35wh41`) מייצרת שתי תמונות ב-kie.ai, מכווצת אותן, ומבצעת commit לענף `master` במאגר `PointStarIL/marcuslaw-website` ← GitHub Actions פורס לשרת קישורים ← הקובץ עובר ל"מאמרים שפורסמו".

- תיקיית Drive "מאמרים חדשים" (אחסון שיתופי "מיתוג"): `https://drive.google.com/drive/folders/1yqiqCj4rILSU6cizFsOi8rde64KiLa7C`
- Credentials בסדנה: `kie.ai API` (Header: Authorization = `Bearer <key>`), `GitHub | marcuslaw-website | contents`
- פרטי הפריסה: `CLAUDE.md` במאגר הוא מקור האמת.

## שלב 1: מקור

- פסק דין מהמסד: `C:\Users\Chaim\Cowork\ניהול תיקים - ביטוח לאומי\פסיקה ביטוח לאומי` (או `פסיקה דיני עבודה`). כרטיסי-אב ב-`כרטיסים`, טקסט נקי ב-`קבצי פסקי דין\*.md`. לקרוא את הטקסט המלא, לא רק את הכרטיס.
- אם חיים לא בחר, להציע 2-3 פסקי דין אחרונים (לפי תאריך שינוי של הכרטיסים) ב-AskUserQuestion, עם המלצה.
- או חומר שחיים מצרף.

## שלב 2: ניסוח

לטעון את `write-website-article` ולפעול לפיו (מבנה, סגנון סיפורי, פרומפטים לתמונות). בנוסף:
- רק מה שכתוב במקור. ציטוטים מילה במילה ורק מהמקור. לא להמציא פסיקה.
- אנונימיות: בלי שמות צדדים ועורכי דין, בלי מספר תיק, בלי תאריכים מדויקים, סכומים מעוגלים ("כ-140 אלף ש"ח"), מקום עבודה כללי.
- `category`: `insurance` / `labor` / `realestate`.
- שם הקובץ = ה-slug שהסדנה תגזור מ-`title_en`.

## שלב 3: בדיקה לפני העלאה

להריץ בדיקה מקומית שמדמה את צומת Parse Markdown:
- frontmatter תקין בין `---` ו-`---`, עם כל השדות (title_he, title_en, description_he, description_en, category, image_hero, image_inline).
- כותרות `## עברית` ו-`## English` קיימות.
- slug: `title_en` באותיות קטנות, הסרת תווים שאינם `a-z0-9 -`, רווחים למקפים, עד 60 תווים.
- אין מקף ארוך.
- ה-slug לא קיים כבר ב-`src/routes/articles/` במאגר.

## שלב 4: אישור חיים

לשלוח לחיים את הקובץ (SendUserFile) ולשאול ב-AskUserQuestion אם לפרסם. **ההעלאה מפרסמת באתר החי, ולכן לא מעלים בלי "כן" מפורש.**

## שלב 5: העלאה ל-Drive דרך Chrome

אין קונקטור Drive. עובדים ב-Claude in Chrome (לטעון את הסקיל `chrome-browser`):
1. לשמור את הקובץ גם ב-`C:\Users\Chaim\Cowork\Claude outputs\` (device_commit_files).
2. לפתוח את תיקיית "מאמרים חדשים" בטאב חדש.
3. אם כבר יש בתיקייה קובץ באותו שם (ניסיון קודם שנכשל): לבחור את השורה, Delete, ולאשר "העברה לאשפה". הסדנה מופעלת רק על קובץ **חדש**, ולכן צריך למחוק ולהעלות מחדש.
4. להזריק לדף `input type=file` (javascript_tool), לאתר אותו ב-find, ולהעלות אליו ב-`file_upload` את הקובץ **מנתיב הקונטיינר** (נתיב מקומי במחשב נדחה).
5. לשלוח לאזור ה-drop (המחלקה `.PFjZL`, או `[role=main]`) את האירועים dragenter, dragover ו-drop עם DataTransfer שמכיל את הקובץ, ולהסיר את ה-input.
6. לוודא שהשורה מופיעה בתיקייה, ולסגור את הטאב.

## שלב 6: מעקב ואימות

- הטריגר בודק כל דקה, והתמונות לוקחות כדקה. לחכות כ-3 דקות ואז `search_workflow_executions` על `MjSYn6FSge35wh41`.
- בהצלחה: `git fetch` למאגר ולוודא commit בשם `Add article: <slug> (n8n)` עם 7 קבצים; `gh run list -R PointStarIL/marcuslaw-website -L 1` מראה Deploy to production = success.
- באתר: `https://marcus-law.co.il/articles/<slug>/` מחזיר 200, ושתי התמונות (`/images/articles/<slug>.jpg` ו-`-inline.jpg`) מחזירות 200 ושוקלות בערך 100KB.
- לדווח לחיים: קישור לדף, ומה נבדק.

## תקלות מוכרות

| הודעה בסדנה | פירוש | מה לעשות |
|---|---|---|
| kie.ai Rejected Request עם 401 | ה-Credential של kie.ai שגוי | לבקש מחיים לבדוק ש-Value הוא `Bearer ` ואחריו המפתח |
| kie.ai Rejected Request עם output_format | kie.ai שינה ערכים מותרים | ב-nano-banana-2 מותר `jpg` או `png` בלבד |
| Article Already Exists | ה-slug כבר במאגר | לשנות את `title_en` ולהעלות שוב |
| Image Generation Failed | התמונות נכשלו או לקחו יותר מ-15 דקות | למחוק את הקובץ מהתיקייה ולהעלות שוב |
| שגיאה בצמתי GitHub | טוקן פג או חסר הרשאה | הטוקן ב-Infisical `/apps/website` → `CONTENTS_KEY`; לחדש ולעדכן את ה-Credential |

בכל כישלון שלפני Update Master לא נכתב דבר למאגר, והאתר לא השתנה. אם ה-build נשבר ב-GitHub Actions, הפריסה לא מתבצעת והאתר הקודם נשאר.