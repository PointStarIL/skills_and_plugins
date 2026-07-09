# התקנה — local-ocr-folder (Windows)

התקנה חד-פעמית בכל מחשב. כל הרכיבים מקומיים; שום דבר לא נשלח לענן.

## 1. Tesseract OCR (מנוע ה-OCR)

הורד את בילד ה-Windows של **UB Mannheim**:

- https://github.com/UB-Mannheim/tesseract/wiki

בזמן ההתקנה:

1. בחר "Additional language data" והוסף **Hebrew (heb)**. אם קיים גם **heb_old** — סמן אותו (כתיב חסר/עברית ישנה). English (`eng`) מותקן כברירת מחדל.
2. סמן "Add Tesseract to PATH" (מומלץ). אם לא — רשום את נתיב ההתקנה, למשל `C:\Program Files\Tesseract-OCR\tesseract.exe`.

אם Tesseract לא ב-PATH, הגדר משתנה סביבה לפני ההרצה:

```bat
set TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

הסקריפטים קוראים את המשתנה `TESSERACT_CMD` אם הוא מוגדר.

## 2. Python וחבילות

התקן Python 3.10+ (https://www.python.org/downloads/windows/), ואז:

```bat
pip install pymupdf pytesseract pillow opencv-python numpy
```

- **pymupdf** — רסטור עמודי PDF לתמונות + זיהוי שכבת טקסט (מחליף את Poppler; אין צורך בבינארי חיצוני).
- **pytesseract** — עטיפת Python ל-Tesseract.
- **pillow** — עיבוד תמונה.
- **opencv-python** + **numpy** — יישור הטיה, בינריזציה, הסרת רעש.

## 3. אימות

```bat
python scripts\check_deps.py
```

הפלט מפרט מה מותקן ומה חסר, בלי לגעת בשום מסמך. אל תמשיך עד שמתקבל `OK`.

## הערות

- **אין צורך ב-Poppler** — PyMuPDF עושה את הרסטור. אם בעתיד תרצה Poppler, אפשר להוסיף, אך הסקריפטים לא דורשים אותו.
- `heb_old` אינו חובה. אם אינו מותקן, ה-OCR ירוץ עם `heb+eng` וידווח על כך בלבד.
