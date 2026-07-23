# party-claims-extractor

פלאגין Claude Code מקומי שעושה דבר אחד: **חילוץ וסיווג טענות הצדדים מכתבי ערר
וכתבי תשובה, והפקת מסמך Word** עם תמצית מובנית ונייטרלית.

עצמאי לגמרי — **אין תלות ב-legal-ai, ב-MCP או במסד נתונים.** החילוץ נעשה בכוח ההיסק
של המודל, מונחה במדריך הארוז (`skills/extract-party-claims/claims-extraction-guide.md`).

## מה הוא עושה
1. קורא כתבי ערר / תשובה מקומיים (PDF / DOCX / TXT).
2. מחלץ ומסווג את טענות כל צד — טענות סף מול טענות לגופו של עניין, מאורגן תמטית
   לפי ראש טיעון, בקול הפעיל של הצד, בניטרליות מלאה.
3. מפיק קובץ Word (`.docx`) בעברית RTL עם התמצית.

## התקנה

### הדרך הפשוטה — טעינה ישירה (מומלץ לשימוש מקומי)
```bash
claude --plugin-dir /home/chaim/party-claims-extractor
```
אחרי שינוי בקבצים: `/reload-plugins`.

### התקנה קבועה דרך marketplace מקומי
```
/plugin marketplace add /home/chaim/party-claims-extractor
/plugin install party-claims-extractor@marcus-law-plugins
```

## שימוש
בתוך פרויקט Claude Code, עם הקבצים בהישג יד:
```
/party-claims-extractor:extract-party-claims ./כתב-ערר.pdf ./כתב-תשובה.docx
```
או פשוט בקש: "חלץ את טענות הצדדים מהקבצים האלה והפק מסמך Word".

הפלט: `תמצית טענות הצדדים.docx` ב-cwd, וקובץ ביניים `claims.json`.

## דרישה טכנית אחת
הפקת ה-Word משתמשת ב-`python-docx`. אם חסר:
```bash
pip install python-docx
```
(קריאת קבצי `.docx` כקלט משתמשת באותה חבילה; PDF נקרא נייטיב ע"י Claude.)

## מבנה
```
party-claims-extractor/
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── skills/extract-party-claims/
│   ├── SKILL.md                      # ה-workflow
│   └── claims-extraction-guide.md    # מדריך החילוץ (מקור-האמת לסיווג/ארגון)
├── scripts/
│   ├── build_claims_docx.py          # JSON → Word (RTL)
│   └── read_docx.py                  # חילוץ טקסט מ-.docx לקלט
└── README.md
```

## מה הפלאגין הזה *לא* עושה (במכוון)
- אין חיפוש בקורפוס/תקדימים, אין תיקים דומים, אין שמירה במסד — אלה דורשים את
  מערכת legal-ai. כאן: קלט מקומי → ניתוח → Word, ותו לא.
