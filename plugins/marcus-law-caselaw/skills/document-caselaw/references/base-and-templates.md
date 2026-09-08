# תבניות ודוגמאות — מסד הפסיקה

## אינדקס פסיקה.base (דוגמה)

תחביר Obsidian Bases. אמת מול הסקיל `obsidian:obsidian-bases` לפני יצירה, שכן
התחביר משתנה בין גרסאות. דורש Obsidian 1.9+.

```yaml
filters:
  and:
    - type == "קביעה"
properties:
  note.topic:
    displayName: נושא הקביעה
  note.citation:
    displayName: מראה מקום
  note.paragraph:
    displayName: פסקה
  note.status:
    displayName: סטטוס
  note.tags:
    displayName: תגיות
  note.court:
    displayName: ערכאה
views:
  - type: table
    name: כל הקביעות
    order:
      - note.topic
      - note.citation
      - note.paragraph
      - note.status
      - note.tags
  - type: table
    name: מאושרות בלבד
    filters:
      and:
        - status == "מאושר"
    order:
      - note.topic
      - note.citation
      - note.paragraph
      - note.tags
  - type: table
    name: ממתינות לאישור
    filters:
      and:
        - status == "ממתין"
    order:
      - note.topic
      - note.citation
      - note.paragraph
  - type: cards
    name: כרטיסיות
    order:
      - note.topic
      - note.citation
```

## תבנית כרטיס-אב (כרטיסים/<שם>.md)

```markdown
---
type: פסק דין
citation: <אזכור אחיד מלא>
court: <ערכאה>
date: <YYYY-MM-DD>
outcome: <תוצאה בקצרה>
source_file: קבצי פסקי דין/<שם הקובץ>
aliases:
  - <כינוי מקוצר>
---

## מטא-דאטה

| שדה | ערך |
|---|---|
| הרכב | <שופטים> |
| ב"כ המבקש/ת | <עו"ד> |
| ב"כ המשיב | <עו"ד> |

## תמצית ההליך

<2-4 שורות>

## קביעות בפסק דין

- [[<קישור לפתק קביעה 1>]]
- [[<קישור לפתק קביעה 2>]]
```

## תבנית פתק קביעה (קביעות/<נושא>.md)

```markdown
---
type: קביעה
pesak_din: "[[<כרטיס-האב>]]"
topic: <נושא הקביעה במשפט>
citation: <אזכור אחיד מלא>
paragraph: <מספר פסקה>
court: <ערכאה>
date: <YYYY-MM-DD>
status: ממתין
tags:
  - <תגית_עם_קו_תחתון>
---

> [!quote] פסקה <מספר>
> <ציטוט מדויק מפסק הדין, מילה במילה>

**שימוש בטיעון:** <מתי הקביעה שימושית, לפי מה שכתוב בפסק הדין בלבד>
```
