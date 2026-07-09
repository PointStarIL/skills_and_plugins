#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
llm_config.py — שכבת קונפיג משותפת לחיבור Gemma המקומי (LM Studio, LAN).

גם local-redact וגם כל שימוש עתידי ב-Gemma קוראים מכאן.

חוק הברזל: הסקריפט מדבר עם Gemma על הרשת הפנימית. הטוקן לעולם לא מקודד כאן —
הוא נלקח ממשתנה הסביבה LMSTUDIO_API_KEY או מקובץ .env מקומי שאינו נכנס ל-git.
"""

import os


# --- ברירות מחדל (ניתנות לעקיפה ע"י משתני סביבה) ---
BASE_URL = os.environ.get("GEMMA_BASE_URL", "http://192.168.10.216:1234/v1")
MODEL = os.environ.get("GEMMA_MODEL", "google/gemma-4-e4b")

# timeout לשנייה לכל בקשה (מודל מקומי — לתת מרווח)
REQUEST_TIMEOUT = int(os.environ.get("GEMMA_TIMEOUT", "120"))


def _load_dotenv():
    """טוען .env מקומי אם קיים (תיקיית העבודה או תיקיית הפרויקט), בלי תלות חיצונית.
    לא דורס משתני סביבה שכבר מוגדרים."""
    candidates = []
    cwd = os.getcwd()
    candidates.append(os.path.join(cwd, ".env"))
    # חפש כלפי מעלה עד 4 רמות
    d = cwd
    for _ in range(4):
        d = os.path.dirname(d)
        if not d:
            break
        candidates.append(os.path.join(d, ".env"))

    for path in candidates:
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k and k not in os.environ:
                        os.environ[k] = v
        except OSError:
            continue


def get_api_key():
    """מחזיר את הטוקן ממשתנה סביבה / .env. LM Studio לרוב מקבל כל טוקן,
    ולכן ברירת המחדל 'lm-studio' תקפה אם לא הוגדר דבר."""
    _load_dotenv()
    return os.environ.get("LMSTUDIO_API_KEY", "lm-studio")
