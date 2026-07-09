#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preflight_gemma.py — בדיקת זמינות של שרת Gemma לפני ריצה.

בודק GET /v1/models. אם השרת כבוי / הפורט חסום — נעצר עם הודעה ברורה,
כדי לא ליפול באמצע תהליך ההשחרה. יוצא 0 אם זמין, 1 אם לא.
"""

import sys
import json

from _common import list_models


def main():
    ok, info = list_models()
    if ok:
        print(f"[OK] Gemma זמין: {info['url']}")
        print(f"     מודלים זמינים: {', '.join(info['models']) or '(אין)'}")
        if info["target_present"]:
            print(f"     מודל היעד '{info['target']}' — נמצא.")
        else:
            print(f"     אזהרה: מודל היעד '{info['target']}' לא ברשימה. "
                  f"עדכן GEMMA_MODEL או טען אותו ב-LM Studio.")
        print("\n--- JSON ---")
        print(json.dumps(info, ensure_ascii=False, indent=2))
        sys.exit(0)
    else:
        print(f"[חסר] Gemma לא זמין בכתובת {info['url']}")
        print(f"       שגיאה: {info['error']}")
        print("       ודא ש-LM Studio פועל, שהמודל טעון, ושהפורט פתוח ב-LAN.")
        print("       אפשר להמשיך בהשחרה עם --engine regex (בלי Gemma).")
        print("\n--- JSON ---")
        print(json.dumps(info, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
