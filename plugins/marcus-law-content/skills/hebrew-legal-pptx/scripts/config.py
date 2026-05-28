"""
config.py — הגדרות גלובליות לסקיל hebrew-legal-pptx.

⚠️ אבטחה: קובץ זה מכיל API key. אין להעלות לגיט פומבי.
"""

# ====================================================================
# KIE.AI API
# ====================================================================
# מפתח API ל-kie.ai (ליצירת תמונות).
# ניתן לדרוס דרך משתנה הסביבה KIE_API_KEY.
KIE_API_KEY = "4fe4a99aff1fa920e17ad8635122c4f7"

# Endpoint בסיסי
KIE_BASE_URL = "https://api.kie.ai/api/v1/jobs"

# ====================================================================
# Image generation defaults
# ====================================================================
# מודל ברירת מחדל ליצירת תמונות.
# אפשרויות נפוצות (text-to-image):
#   - "google/nano-banana"       — מהיר, איכות טובה, זול
#   - "google/imagen4-fast"      — מהיר עם איכות גבוהה ומהירות טובה
#   - "google/imagen4"           — איכות גבוהה יותר, איטי יותר
#   - "google/imagen4-ultra"     — האיכות הגבוהה ביותר של Google
#   - "bytedance/seedream-v4-text-to-image"  — איכות גבוהה
#   - "openai/gpt-image-2"       — GPT Image 2 (טוב לטקסט בתמונה)
DEFAULT_IMAGE_MODEL = "google/imagen4-fast"

# Timeout לפולינג (שניות)
POLL_TIMEOUT = 300  # 5 דקות
POLL_INTERVAL = 3   # 3 שניות בין בדיקות
