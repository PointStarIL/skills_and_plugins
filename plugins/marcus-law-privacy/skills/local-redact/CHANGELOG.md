# CHANGELOG — local-redact

## 0.2.0
- זיהוי ישויות עבר ל-Gemma מקומי (LM Studio, endpoint תואם-OpenAI ב-LAN).
- שכבת קונפיג משותפת references/llm_config.py + טעינת .env (טוקן לא בקוד).
- preflight_gemma.py, detect_entities.py, map_boxes.py, review.py, burn_redactions.py.
- שער אנושי: הצריבה נפרדת (--burn) אחרי preview.
- Fallback ל-regex + רשימת ישויות (--engine gemma|regex|both).

## 0.1.0
- גרסה ראשונה מבוססת regex + רשימת ישויות (הפכה ל-fallback).
