# סקיל make-hebrew-slides - גרסה מתוקנת

## מה תוקן?
1. **הקובץ pptx_builder.py היה קטוע** (555 שורות במקום 753 שורות)
   - חסרו המתודות `_fill_text`, `_add_title`, `_add_bullets`, `_add_column`
   - חסר חלק מ-`_add_footer`
2. **גודל פונט אוטומטי** - בשקפים עם הרבה טקסט הסקיל מתאים אוטומטית את הגודל ל-18-22pt
3. **קובץ icons.py חדש** - ספריית איקונים וקטוריים מצוירים ישירות (פטיש, מאזניים, מסמך, בניין, אנשים, מפה+פין)

## איך להתקין?
1. סגור את Cowork אם פתוח
2. לך לתיקיית הסקיל המקורי:
   ```
   C:\Users\Chaim\AppData\Roaming\Claude\local-agent-mode-sessions\skills-plugin\9509084e-7913-4525-860f-da05b83a1a96\8db6e213-b9c0-4e1f-9185-f67af7939695\skills\make-hebrew-slides\
   ```
3. החלף את הקבצים:
   - `scripts\pptx_builder.py` ← מתיקיית `SKILL_FIXED\scripts\pptx_builder.py`
   - הוסף `scripts\icons.py` (חדש) ← מתיקיית `SKILL_FIXED\scripts\icons.py`

## איך להפעיל יצירת תמונות AI?
הסביבה הסנדבוקסית של Cowork חוסמת גישה ל-api.kie.ai.
כדי ליצור תמונות, הרץ את הסקריפט מהמחשב שלך:

```
cd "C:\Users\Chaim\Documents\Claude\Projects\מצגת תקיפת החלטה ועדה מקומית\SKILL_FIXED"
python generate_images.py
```

## מה כולל הסקיל המתוקן?
- `scripts/pptx_builder.py` (גרסה מלאה, 753 שורות)
- `scripts/icons.py` (חדש - איקונים וקטוריים)
- `scripts/image_generator.py` (יצירת תמונות AI)
- `scripts/embed_fonts.py` (הטמעת פונטים)
- `scripts/config.py` (הגדרות API)
- `fonts/` (Suez One + Rubik)
- `generate_images.py` (סקריפט ליצירת 6 התמונות לשקפי המצגת)
