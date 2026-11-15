#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_folder.py - שער אימות לארגון תיקיית ערר או תיקיית לקוח.

הסכנה בסקיל שמארגן תיקייה אינה שהוא יטעה בשם קובץ, אלא ש**קובץ ייעלם**:
הועבר לתת-תיקייה שגויה, נדרס בשם זהה, או נמחק אחרי העתקה שנכשלה חלקית.
טעות כזו שקטה, ומתגלה כשמחפשים את המסמך ולא מוצאים.

הסקריפט סופר. הוא משווה את קבצי המקור לקבצים שבתוצאה ומוודא שכל אחד
נמצא, שאין קובץ יתום בשורש, ושכל PDF נושא שכבת טקסט.

ארבע הבדיקות:
  1. שלמות   - כל קובץ מקור מיוצג בתוצאה, לפי גודל ותוכן
  2. שורש    - לא נשאר קובץ לא ממוין בשורש התיקייה
  3. טקסט    - לכל PDF יש שכבת טקסט שניתן לחפש בה
  4. סיכום   - מסמך הסיכום נוצר

קודי יציאה: 0 תקין, 1 נמצאו הפרות, 2 שגיאת קלט.
"""

import hashlib
import os
import sys

PDF_EXT = ".pdf"
# תיקיות שאינן חלק מהתוצאה ואין לספור את תוכנן.
SKIP_DIRS = {"__pycache__", ".git", "_ocr_out", ".DS_Store"}
# סיומות שנוצרות בתהליך ואינן קובץ מקור שאבד.
DERIVED_EXT = {".md", ".txt", ".tsv", ".json"}


class Finding:
    __slots__ = ("severity", "check", "message")

    def __init__(self, severity, check, message):
        self.severity = severity
        self.check = check
        self.message = message

    def as_dict(self):
        return {"severity": self.severity, "check": self.check,
                "message": self.message}


def _walk(root):
    """מחזיר {נתיב יחסי: גודל} לכל קובץ, בלי תיקיות עזר."""
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn.startswith("~$") or fn == ".DS_Store":
                continue
            full = os.path.join(dirpath, fn)
            try:
                out[os.path.relpath(full, root)] = os.path.getsize(full)
            except OSError:
                continue
    return out


def _digest(path, limit=1 << 20):
    """טביעת אצבע של תחילת הקובץ. מספיקה לזיהוי, זולה על תיקייה גדולה."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            h.update(fh.read(limit))
    except OSError:
        return None
    return h.hexdigest()


def _pdf_has_text(path, min_chars=20):
    """
    האם ל-PDF יש שכבת טקסט. מחזיר None אם לא ניתן לבדוק.

    הסף אינו 0: קובץ סרוק מחזיר לעיתים כמה תווי זבל מכותרת או מחותמת,
    וסף אפס היה מסמן אותו כאילו יש בו טקסט.
    """
    try:
        import fitz
    except ImportError:
        return None
    try:
        doc = fitz.open(path)
    except Exception:  # noqa: BLE001
        return None
    try:
        total = 0
        for page in doc:
            total += len(page.get_text().strip())
            if total >= min_chars:
                return True
        return False
    finally:
        doc.close()


def validate(source_dir, result_dir, summary_glob=None, check_text=True):
    findings = []

    src = _walk(source_dir)
    res = _walk(result_dir)

    # --- בדיקה 1: שלמות ---
    res_by_size = {}
    for rel, size in res.items():
        res_by_size.setdefault(size, []).append(rel)

    for rel, size in sorted(src.items()):
        if os.path.splitext(rel)[1].lower() in DERIVED_EXT:
            continue
        candidates = res_by_size.get(size, [])
        if not candidates:
            findings.append(Finding(
                "RED", "1-completeness",
                "קובץ מקור לא נמצא בתוצאה: {0}".format(rel)))
            continue
        if len(candidates) > 1:
            want = _digest(os.path.join(source_dir, rel))
            if want and not any(
                    _digest(os.path.join(result_dir, c)) == want for c in candidates):
                findings.append(Finding(
                    "RED", "1-completeness",
                    "קובץ בגודל תואם נמצא אך התוכן שונה: {0}".format(rel)))

    # --- בדיקה 2: שורש נקי ---
    # מסמך הסיכום יושב בשורש במתכוון בחלק מהפריסות, ולכן אינו קובץ יתום.
    summary_files = set()
    if summary_glob:
        summary_files = {r for r in res if summary_glob in os.path.basename(r)}

    for rel in sorted(res):
        if os.sep in rel or "/" in rel:
            continue
        if os.path.splitext(rel)[1].lower() in DERIVED_EXT:
            continue
        if rel in summary_files:
            continue
        findings.append(Finding(
            "RED", "2-root",
            "קובץ נשאר לא ממוין בשורש: {0}".format(rel)))

    # --- בדיקה 3: שכבת טקסט ---
    if check_text:
        unknown = 0
        for rel in sorted(res):
            if not rel.lower().endswith(PDF_EXT):
                continue
            has = _pdf_has_text(os.path.join(result_dir, rel))
            if has is None:
                unknown += 1
            elif not has:
                findings.append(Finding(
                    "RED", "3-textlayer",
                    "PDF בלי שכבת טקסט: {0}".format(rel)))
        if unknown:
            findings.append(Finding(
                "ORANGE", "3-textlayer",
                "{0} קובצי PDF לא נבדקו (pymupdf חסר או קובץ פגום). "
                "לא נבדק, לא 'עבר'.".format(unknown)))

    # --- בדיקה 4: מסמך סיכום ---
    if summary_glob:
        if not summary_files:
            findings.append(Finding(
                "RED", "4-summary",
                "מסמך הסיכום לא נמצא (חיפוש: {0})".format(summary_glob)))

    return findings, len(src), len(res)


def status_of(findings):
    if any(f.severity == "RED" for f in findings):
        return "נכשל"
    if any(f.severity == "ORANGE" for f in findings):
        return "עבר עם הערות"
    return "עבר"


_CHECK_NAMES = {
    "1-completeness": "שלמות הקבצים",
    "2-root": "שורש נקי",
    "3-textlayer": "שכבת טקסט",
    "4-summary": "מסמך סיכום",
}


def format_report(findings, n_src, n_res):
    bar = "=" * 62
    status = status_of(findings)
    lines = [bar, "דוח אימות ארגון תיקייה", bar, "",
             "סטטוס: {0}".format(status), "",
             "קבצים במקור: {0}".format(n_src),
             "קבצים בתוצאה: {0}".format(n_res), "",
             "-" * 62]
    for key in sorted(_CHECK_NAMES):
        group = [f for f in findings if f.check == key]
        red = [f for f in group if f.severity == "RED"]
        orange = [f for f in group if f.severity == "ORANGE"]
        if red:
            mark, note = "✗ נכשל", "{0} הפרות".format(len(red))
        elif orange:
            mark, note = "⚠ לא נבדק", orange[0].message[:34]
        else:
            mark, note = "✓ עבר", "0 ממצאים"
        lines.append("{0:<18} {1:<12} {2}".format(_CHECK_NAMES[key], mark, note))
    lines.append("-" * 62)
    lines.append("")
    if findings:
        lines.append("ממצאים")
        order = {"RED": 0, "ORANGE": 1}
        for f in sorted(findings, key=lambda x: (order[x.severity], x.check)):
            icon = "✗" if f.severity == "RED" else "⚠"
            lines.append("  {0} [{1}] {2}".format(
                icon, _CHECK_NAMES[f.check], f.message))
        lines.append("")
    lines.append("המלצה:")
    if status == "נכשל":
        lines.append("  אל תמחק את קבצי המקור. תקן את הממצאים והרץ שוב.")
    elif status == "עבר עם הערות":
        lines.append("  השלם את מה שלא נבדק לפני שמוחקים את המקור.")
    else:
        lines.append("  הארגון שלם. ניתן להמשיך.")
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
        description="אימות שארגון תיקייה לא איבד קבצים. "
                    "קוד יציאה 0 תקין, 1 הפרות, 2 שגיאת קלט.")
    ap.add_argument("source", help="תיקיית המקור (לפני הארגון)")
    ap.add_argument("result", help="התיקייה המאורגנת")
    ap.add_argument("--summary", default=None,
                    help="מחרוזת שחייבת להופיע בשם מסמך הסיכום, למשל 'סיכום'")
    ap.add_argument("--no-text-check", action="store_true",
                    help="דלג על בדיקת שכבת הטקסט ב-PDF")
    ap.add_argument("--json", action="store_true", help="פלט JSON")
    args = ap.parse_args(argv)

    for d in (args.source, args.result):
        if not os.path.isdir(d):
            sys.stderr.write("לא נמצאה תיקייה: {0}\n".format(d))
            return 2

    findings, n_src, n_res = validate(
        args.source, args.result, args.summary, not args.no_text_check)
    status = status_of(findings)

    if args.json:
        print(json.dumps({
            "status": status,
            "files_source": n_src,
            "files_result": n_res,
            "findings": [f.as_dict() for f in findings],
        }, ensure_ascii=False, indent=2))
    else:
        print(format_report(findings, n_src, n_res))

    return 1 if status == "נכשל" else 0


if __name__ == "__main__":
    raise SystemExit(main())
