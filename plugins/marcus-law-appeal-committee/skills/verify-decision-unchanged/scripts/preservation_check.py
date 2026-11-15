#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preservation_check.py - אימות שסידור-מחדש של החלטה לא שינה תוכן.

מקבל שני קבצים, המקור והמסודר, ובודק שאף פסקה לא אבדה, שאף תוכן חדש לא
נוצר, ושהציטוטים, ההפניות והתוצאה האופרטיבית נשמרו מילה במילה.

שש הבדיקות תואמות לאלה שב-SKILL.md:

  1. שימור פסקאות   - פסקה שאבדה או פסקה שנוצרה יש מאין
  2. שימור ציטוטים   - כל מובאה בגרשיים חייבת להופיע כלשונה
  3. שימור הפניות    - עע"מ, ערר, סעיף לחוק, מספר תכנית
  4. תוצאה אופרטיבית - "סוף דבר" חייב להיות זהה בדיוק
  5. שימור משמעות    - סטיית אורך מעל 10 אחוז, אזהרה בלבד
  6. מילות קישור     - רק מהרשימה הסגורה

עד היום הבדיקות האלה בוצעו בעין של המודל לפי פסאודו-קוד. הבעיה: אותו
מודל שסידר מחדש הוא שבדק, ובדיוק סוג הטעות שהסידור עלול לייצר, השמטת
פסקה, הוא מה שקריאה חוזרת נוטה לפספס. סקריפט סופר.

חומרות:
  RED        הפרת כלל ברזל. הסקיל המארגן לא מחזיר את התוצאה.
  DOUBLE_RED שינוי בתוצאה האופרטיבית. החמור ביותר.
  ORANGE     חשד שדורש עין אנושית.
  GREEN      שינוי מותר, מתועד לשקיפות.

קודי יציאה: 0 עבר או עבר-עם-הערות, 1 נכשל, 2 שגיאת קלט.
"""

import difflib
import os
import re
import sys
import unicodedata

# ---------------------------------------------------------------------------
# מילות הקישור המותרות. הרשימה סגורה בכוונה, וזהה לזו שב-SKILL.md של
# reorder-decision-sections. תוספת שאינה כאן היא הפרה.
# ---------------------------------------------------------------------------
ALLOWED_CONNECTORS = [
    "בנוסף,", "בנוסף לאמור,", "לעניין זה,", "מנגד,", "כפי שצוין לעיל,",
    "ראו לעניין זה,", "מן הכלל אל הפרט,", "ובענייננו,", "סיכומו של דבר,",
    "אכן,", "יחד עם זאת,", "נקדים ונציין כי,", "ודוק,", "נחדד כי,",
    "היינו,", "ללמדך כי,", "הנה כי כן,", "דא עקא,", "למעלה מן הצורך,",
    "טרם סיום נבקש לציין כי,",
]

# פותח את החלק האופרטיבי. ההחלטה מסתיימת שם, ולכן כל שינוי בו הוא שינוי
# בתוצאה עצמה ולא בסידור.
OPERATIVE_MARKERS = [
    "סוף דבר", "סיכומו של דבר", "אשר על כן אנו מחליטים",
    "אשר על כן, אנו מחליטים", "לסיכום", "התוצאה",
]

# הפניות משפטיות. כל אחת נבדקת כמחרוזת מנורמלת ולא כמשמעות.
REF_PATTERNS = [
    r'עע"?מ\s*\d+/\d+',
    r'בג"?ץ\s*\d+/\d+',
    r'רע"?א\s*\d+/\d+',
    r'ע"?א\s*\d+/\d+',
    r'ע"?פ\s*\d+/\d+',
    r'עת"?מ\s*\d+/\d+',
    r'ערר\s*\d+/\d+',
    r'ה"?פ\s*\d+/\d+',
    r'סעיף\s+\d+[א-ת]?(?:\([^)]{1,6}\))*\s+לחוק',
    r'תקנה\s+\d+[א-ת]?\s+לתקנות',
    r'תב"?ע\s*[א-ת]{0,3}[/\-]?\d+',
    r'תכנית\s+[א-ת]{1,4}[/\-]\d+[א-ת]?',
    r'מי[/\-]\d+[א-ת]?',
]

_DIRECTIONAL = dict.fromkeys(map(ord, "‎‏‪‫‬‭‮"), None)
_QUOTE_CHARS = '"״“”„«»'

MEANING_DRIFT_TOLERANCE = 0.10
PARAGRAPH_MATCH_THRESHOLD = 0.95
NEAR_MATCH_THRESHOLD = 0.80


# ---------------------------------------------------------------------------
# נורמליזציה
# ---------------------------------------------------------------------------

def normalize(text):
    """מסיר תווי כיווניות, מאחד גרשיים ומכווץ רווחים. לא נוגע באותיות."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_DIRECTIONAL)
    for ch in _QUOTE_CHARS:
        text = text.replace(ch, '"')
    text = text.replace("’", "'").replace("׳", "'")
    text = re.sub(r"[–—―]", "-", text)
    return re.sub(r"\s+", " ", text).strip()


def similarity(a, b):
    return difflib.SequenceMatcher(None, normalize(a), normalize(b)).ratio()


# ---------------------------------------------------------------------------
# קריאת קלט
# ---------------------------------------------------------------------------

def read_paragraphs(path):
    """מחזיר רשימת פסקאות לא ריקות מ-DOCX או מקובץ טקסט."""
    with open(path, "rb") as fh:
        head = fh.read(2)

    if head == b"PK":
        try:
            import docx
        except ImportError:
            raise SystemExit("חסר python-docx לקריאת DOCX. התקן: pip install python-docx")
        d = docx.Document(path)
        paras = [p.text for p in d.paragraphs]
        for t in d.tables:
            for row in t.rows:
                for cell in row.cells:
                    paras.extend(p.text for p in cell.paragraphs)
    else:
        with open(path, encoding="utf-8", errors="replace") as fh:
            paras = re.split(r"\n\s*\n", fh.read())

    return [p.strip() for p in paras if p and p.strip()]


# ---------------------------------------------------------------------------
# חילוץ
# ---------------------------------------------------------------------------

_ABBREV_GERSHAYIM = re.compile('(?<=[א-ת])"(?=[א-ת])')
# תו מאזור השימוש הפרטי. לא יופיע בטקסט אמיתי, ולכן בטוח כסמן זמני.
_ABBREV_PLACEHOLDER = chr(0xE000)


def strip_abbreviation_quotes(text):
    """
    מנטרל גרשיים של ראשי תיבות לפני איתור מובאות.

    בעברית משפטית הגרשיים משמשים לשני דברים שונים: מובאה, וראשי תיבות
    (עע"מ, בג"ץ, ת"א, ב"כ, ז"ל). ההבדל הצורני חד: בראשי תיבות הגרשיים
    יושבים **בין שתי אותיות עבריות**, ובמובאה הם גובלים ברווח או בסימן
    פיסוק.

    בלי ההפרדה הזו הגרשיים של עע"מ מזדווגים עם פתיחת המובאה האמיתית,
    והתוצאה היא "ציטוט" מומצא שבולע את הטקסט שביניהם. זה נתפס בבדיקה
    test_pure_reorder_passes: סידור-מחדש נקי דווח כאילו איבד ציטוט.
    """
    return _ABBREV_GERSHAYIM.sub(_ABBREV_PLACEHOLDER, text)


def extract_quotes(text):
    """
    מובאות בתוך גרשיים כפולים, באורך של 4 מילים לפחות.

    הסף אינו שרירותי: מובאה משפטית אמיתית ארוכה, ואילו מחרוזת קצרה
    בגרשיים היא בדרך כלל שם או כינוי. בלי הסף הרעש מטביע את הממצאים.
    """
    out = []
    clean = strip_abbreviation_quotes(normalize(text))
    for m in re.finditer(r'"([^"]{12,})"', clean):
        body = m.group(1).replace(_ABBREV_PLACEHOLDER, '"').strip()
        if len(body.split()) >= 4:
            out.append(body)
    return out


def extract_quotes_all(paragraphs):
    """
    מחלץ מובאות פסקה-פסקה ולא מהטקסט המאוחד.

    חיבור כל הפסקאות למחרוזת אחת מאפשר לגרש סוגר של פסקה אחת להזדווג עם
    גרש פותח של פסקה אחרת, ולייצר מובאה שאינה קיימת באף אחת מהן.
    """
    out = []
    for p in paragraphs:
        out.extend(extract_quotes(p))
    return out


def extract_refs(text):
    norm = normalize(text)
    found = set()
    for pat in REF_PATTERNS:
        for m in re.finditer(pat, norm):
            found.add(re.sub(r"\s+", " ", m.group(0)).strip())
    return found


def extract_operative(paragraphs):
    """הפסקאות מהסמן האופרטיבי ועד הסוף. ריק אם אין סמן."""
    for i, p in enumerate(paragraphs):
        n = normalize(p)
        for marker in OPERATIVE_MARKERS:
            if n.startswith(marker) or n.startswith(marker + ","):
                return paragraphs[i:]
    return []


def leading_addition(original, organized):
    """
    מה נוסף בתחילת הפסקה המסודרת ביחס למקור. מחזיר None אם אין תוספת.
    """
    o, n = normalize(original), normalize(organized)
    if n.endswith(o) and len(n) > len(o):
        return n[: len(n) - len(o)].strip()
    idx = n.find(o[:40]) if len(o) >= 40 else (0 if n.startswith(o) else -1)
    if idx > 0:
        return n[:idx].strip()
    return None


def is_allowed_connector(addition):
    a = normalize(addition).rstrip()
    if not a:
        return True
    return any(a == normalize(c).rstrip() for c in ALLOWED_CONNECTORS)


# ---------------------------------------------------------------------------
# הבדיקות
# ---------------------------------------------------------------------------

class Finding:
    __slots__ = ("severity", "check", "message")

    def __init__(self, severity, check, message):
        self.severity = severity
        self.check = check
        self.message = message

    def as_dict(self):
        return {"severity": self.severity, "check": self.check, "message": self.message}


def _best_match(target, pool):
    best, score = None, 0.0
    for cand in pool:
        r = similarity(target, cand)
        if r > score:
            best, score = cand, r
    return best, score


def check_all(orig_paras, new_paras):
    findings = []

    # --- בדיקה 1: שימור פסקאות ---
    for p in orig_paras:
        match, score = _best_match(p, new_paras)
        if score >= PARAGRAPH_MATCH_THRESHOLD:
            continue
        if score >= NEAR_MATCH_THRESHOLD:
            findings.append(Finding(
                "ORANGE", "1-paragraphs",
                "חשד לשינוי בפסקה (דמיון {0:.0%}): {1}".format(score, p[:80])))
        else:
            findings.append(Finding(
                "RED", "1-paragraphs",
                "פסקה אבדה: {0}".format(p[:80])))

    for p in new_paras:
        _, score = _best_match(p, orig_paras)
        if score < NEAR_MATCH_THRESHOLD:
            findings.append(Finding(
                "RED", "1-paragraphs",
                "פסקה חדשה נוצרה: {0}".format(p[:80])))

    # --- בדיקה 2: שימור ציטוטים ---
    orig_q = extract_quotes_all(orig_paras)
    new_q = set(extract_quotes_all(new_paras))
    for q in orig_q:
        if q in new_q:
            continue
        _, score = _best_match(q, list(new_q))
        if score >= PARAGRAPH_MATCH_THRESHOLD:
            findings.append(Finding(
                "ORANGE", "2-quotes",
                "ציטוט שונה קלות: {0}".format(q[:80])))
        else:
            findings.append(Finding(
                "RED", "2-quotes",
                "ציטוט אבד: {0}".format(q[:80])))

    # --- בדיקה 3: שימור הפניות ---
    orig_r = extract_refs(" ".join(orig_paras))
    new_r = extract_refs(" ".join(new_paras))
    for r in sorted(orig_r - new_r):
        findings.append(Finding("RED", "3-refs", "הפניה אבדה: {0}".format(r)))
    for r in sorted(new_r - orig_r):
        findings.append(Finding("RED", "3-refs", "הפניה חדשה: {0}".format(r)))

    # --- בדיקה 4: תוצאה אופרטיבית ---
    o_op, n_op = extract_operative(orig_paras), extract_operative(new_paras)
    if not o_op and not n_op:
        findings.append(Finding(
            "ORANGE", "4-operative",
            "לא אותר חלק אופרטיבי בשני הקבצים. בדוק ידנית שהתוצאה נשמרה."))
    elif normalize(" ".join(o_op)) != normalize(" ".join(n_op)):
        findings.append(Finding(
            "DOUBLE_RED", "4-operative",
            "התוצאה האופרטיבית שונתה. זו הפרת כלל ברזל חמורה."))

    # --- בדיקה 5: שימור משמעות ---
    for p in orig_paras:
        match, score = _best_match(p, new_paras)
        if match is None or score < NEAR_MATCH_THRESHOLD:
            continue
        a, b = len(normalize(p).split()), len(normalize(match).split())
        if a and abs(b - a) / a > MEANING_DRIFT_TOLERANCE:
            findings.append(Finding(
                "ORANGE", "5-meaning",
                "אורך הפסקה השתנה מ-{0} ל-{1} מילים: {2}".format(a, b, p[:60])))

    # --- בדיקה 6: מילות קישור ---
    for p in orig_paras:
        match, score = _best_match(p, new_paras)
        if match is None or score < NEAR_MATCH_THRESHOLD or score >= 0.999:
            continue
        add = leading_addition(p, match)
        if not add:
            continue
        if is_allowed_connector(add):
            findings.append(Finding(
                "GREEN", "6-connectors",
                'מילת קישור מותרת נוספה: "{0}" לפני "{1}"'.format(add, p[:40])))
        else:
            findings.append(Finding(
                "RED", "6-connectors",
                'תוספת שאינה מילת קישור מותרת: "{0}" לפני "{1}"'.format(add, p[:40])))

    return findings


def status_of(findings):
    if any(f.severity in ("RED", "DOUBLE_RED") for f in findings):
        return "נכשל"
    if any(f.severity == "ORANGE" for f in findings):
        return "עבר עם הערות"
    return "עבר"


# ---------------------------------------------------------------------------
# דיווח
# ---------------------------------------------------------------------------

_ICON = {"DOUBLE_RED": "✗✗", "RED": "✗", "ORANGE": "⚠", "GREEN": "✓"}
_CHECK_NAMES = {
    "1-paragraphs": "שימור פסקאות",
    "2-quotes": "שימור ציטוטים",
    "3-refs": "שימור הפניות",
    "4-operative": "תוצאה אופרטיבית",
    "5-meaning": "שימור משמעות",
    "6-connectors": "מילות קישור",
}


def format_report(orig_paras, new_paras, findings):
    bar = "=" * 62
    status = status_of(findings)
    lines = [bar, "דוח בדיקת שימור", bar, "",
             "סטטוס: {0}".format(status), "",
             "מספר פסקאות במקור: {0}".format(len(orig_paras)),
             "מספר פסקאות בתוצאה: {0}".format(len(new_paras)), ""]

    lines.append("טבלת הבדיקות")
    lines.append("-" * 62)
    for key in sorted(_CHECK_NAMES):
        group = [f for f in findings if f.check == key]
        blocking = [f for f in group if f.severity in ("RED", "DOUBLE_RED")]
        warn = [f for f in group if f.severity == "ORANGE"]
        if blocking:
            mark, note = "✗ נכשל", "{0} הפרות".format(len(blocking))
        elif warn:
            mark, note = "⚠ הערות", "{0} חשדות".format(len(warn))
        else:
            mark, note = "✓ עבר", "0 ממצאים"
        lines.append("{0:<20} {1:<10} {2}".format(_CHECK_NAMES[key], mark, note))
    lines.append("-" * 62)
    lines.append("")

    if findings:
        lines.append("ממצאים")
        order = {"DOUBLE_RED": 0, "RED": 1, "ORANGE": 2, "GREEN": 3}
        for f in sorted(findings, key=lambda x: (order[x.severity], x.check)):
            lines.append("  {0} [{1}] {2}".format(
                _ICON[f.severity], _CHECK_NAMES[f.check], f.message))
        lines.append("")

    lines.append("המלצה:")
    if status == "נכשל":
        lines.append("  לדחות את התוצאה ולחזור לטיוטה המקורית. אל תחזיר את המסמך למשתמש.")
    elif status == "עבר עם הערות":
        lines.append("  לסקור את הממצאים הכתומים אחד-אחד לפני אימוץ.")
    else:
        lines.append("  ניתן לאמץ.")
    lines.append(bar)
    return "\n".join(lines)


def main(argv=None):
    import argparse
    import json

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    ap = argparse.ArgumentParser(
        description="אימות שסידור-מחדש של החלטה לא שינה תוכן. "
                    "קוד יציאה 0 עבר, 1 נכשל, 2 שגיאת קלט.")
    ap.add_argument("original", help="הטיוטה המקורית (DOCX או טקסט)")
    ap.add_argument("organized", help="הטיוטה המסודרת (DOCX או טקסט)")
    ap.add_argument("--json", action="store_true", help="פלט JSON")
    args = ap.parse_args(argv)

    for path in (args.original, args.organized):
        if not os.path.isfile(path):
            sys.stderr.write("לא נמצא קובץ: {0}\n".format(path))
            return 2

    try:
        orig = read_paragraphs(args.original)
        new = read_paragraphs(args.organized)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        sys.stderr.write("שגיאת קריאה: {0}\n".format(e))
        return 2

    if not orig:
        sys.stderr.write("לא חולצו פסקאות מהמקור. אם זה PDF סרוק, הרץ OCR תחילה.\n")
        return 2

    findings = check_all(orig, new)
    status = status_of(findings)

    if args.json:
        print(json.dumps({
            "status": status,
            "paragraphs_original": len(orig),
            "paragraphs_organized": len(new),
            "findings": [f.as_dict() for f in findings],
        }, ensure_ascii=False, indent=2))
    else:
        print(format_report(orig, new, findings))

    return 1 if status == "נכשל" else 0


if __name__ == "__main__":
    raise SystemExit(main())
