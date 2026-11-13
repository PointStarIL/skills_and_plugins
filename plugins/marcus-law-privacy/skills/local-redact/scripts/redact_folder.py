#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
redact_folder.py — entrypoint לשרשרת ההשחרה.

preflight(Gemma) -> detect_entities -> map_boxes -> review -> [burn אם --burn]

ברירת מחדל: engine=both, ועצירה אחרי preview (שער אנושי). הצריבה רק עם --burn.
אם Gemma לא זמין, נופלים אוטומטית ל-regex.

ל-stdout נכתב רק redaction_summary.json (מטא-דאטה). המתזמר אינו רואה תוכן.
"""

import os
import sys
import json
import argparse

from _common import list_models, eprint
import detect_entities as detect_mod
import map_boxes as map_mod
import review as review_mod
import burn_redactions as burn_mod
import verify_redaction as verify_mod


def load_manifest(out_dir):
    with open(os.path.join(out_dir, "manifest.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser(description="שרשרת השחרה מקומית מונעת-Gemma")
    ap.add_argument("out_dir", help="נתיב ל-_ocr_out (פלט ה-OCR)")
    ap.add_argument("--engine", choices=["gemma", "regex", "both"], default="both")
    ap.add_argument("--names", default=None)
    ap.add_argument("--allowlist", default=None)
    ap.add_argument("--enable-dates", action="store_true")
    ap.add_argument("--burn", action="store_true", help="בצע צריבה בלתי-הפיכה (אחרי סקירה)")
    ap.add_argument("--pad", type=int, default=2)
    args = ap.parse_args()

    out_dir = os.path.abspath(args.out_dir)
    if not os.path.isfile(os.path.join(out_dir, "manifest.json")):
        eprint(f"שגיאה: אין manifest.json ב-{out_dir}. הרץ קודם local-ocr-folder.")
        sys.exit(2)

    manifest = load_manifest(out_dir)
    root = manifest.get("root") or os.path.dirname(out_dir)
    docs = manifest["documents"]
    names = map_mod.read_terms(args.names)
    allowlist = map_mod.read_terms(args.allowlist)

    # --- preflight / fallback ---
    gemma_ok = False
    if args.engine in ("gemma", "both"):
        eprint("== preflight: בדיקת Gemma ==")
        ok, info = list_models()
        gemma_ok = ok
        if ok:
            eprint(f"  Gemma זמין ({info['url']}); מודל יעד קיים: {info.get('target_present')}")
        else:
            eprint(f"  Gemma לא זמין: {info.get('error')}")
            if args.engine == "gemma":
                eprint("  נפילה אוטומטית ל-regex.")
            else:
                eprint("  ממשיך עם regex בלבד (חלק ה-both של Gemma מדולג).")

    if args.engine == "regex":
        map_engine = "regex"
    elif args.engine == "gemma":
        map_engine = "gemma" if gemma_ok else "regex"
    else:  # both
        map_engine = "both" if gemma_ok else "regex"

    # --- שלב 2: detect (רק אם Gemma זמין ובשימוש) ---
    if map_engine in ("gemma", "both"):
        eprint("== שלב 2: זיהוי ישויות מול Gemma ==")
        for d in docs:
            try:
                m = detect_mod.detect_document(out_dir, d)
                eprint(f"  [OK] {d['filename']} — {m['total']} ישויות")
            except Exception as e:  # noqa: BLE001
                eprint(f"  [שגיאה] detect {d['filename']}: {e}")

    # --- שלב 3: map ---
    eprint("== שלב 3: מיפוי מלבנים ==")
    summary_docs = []
    for d in docs:
        try:
            meta = map_mod.map_document(out_dir, d, engine=map_engine, names=names,
                                        allowlist=allowlist, enable_dates=args.enable_dates)
        except Exception as e:  # noqa: BLE001
            eprint(f"  [שגיאה] map {d['filename']}: {e}")
            meta = {"total": 0, "by_category": {}, "pages_with_redactions": 0}
        summary_docs.append({"key": d["key"], "filename": d["filename"],
                             "total": meta["total"], "by_category": meta["by_category"],
                             "pages_with_redactions": meta["pages_with_redactions"]})

    # --- שלב 4: review (preview) ---
    eprint("== שלב 4: preview (שער אנושי) ==")
    for d in docs:
        try:
            review_mod.review_document(out_dir, d, pad=args.pad)
        except Exception as e:  # noqa: BLE001
            eprint(f"  [שגיאה] review {d['filename']}: {e}")

    # --- שלב 5: burn (אופציונלי) ---
    burned = False
    verification = {}
    if args.burn:
        eprint("== שלב 5: צריבה בלתי-הפיכה ==")
        burned = True
        for d in docs:
            try:
                burn_mod.burn_document(out_dir, d, root, pad=args.pad)
            except Exception as e:  # noqa: BLE001
                eprint(f"  [שגיאה] burn {d['filename']}: {e}")

        # --- אימות אחרי צריבה: ודא שהערכים שזוהו אינם קריאים בפלט ---
        # לא מדפיסים ערכי שאריות: הם תוכן רגיש, והמתזמר אינו רשאי לראותו.
        # רק ספירה ומספרי עמודים, וגם הם נכנסים ל-redaction_summary.json.
        eprint("== אימות שאריות ==")
        for d in docs:
            try:
                res = verify_mod.verify_document(out_dir, d).get("residuals", [])
                pages = sorted({r["page"] for r in res})
                verification[d["key"]] = {"residuals": len(res), "pages": pages}
                if res:
                    eprint(f"  [אזהרה] {d['filename']}: {len(res)} שאריות אפשריות "
                           f"בעמודים {', '.join(str(p) for p in pages)}. "
                           f"פתח את הקובץ מקומית ובדוק.")
                else:
                    eprint(f"  [OK] {d['filename']}: אימות נקי (0 שאריות).")
            except Exception as e:  # noqa: BLE001
                verification[d["key"]] = {"residuals": None, "pages": [], "error": str(e)}
                eprint(f"  [שגיאה] verify {d['filename']}: {e}")

    # --- סיכום (הפלט היחיד ל-stdout) ---
    for x in summary_docs:
        x["verification"] = verification.get(x["key"])
    # מסמך נחשב "נבדק" רק אם האימות החזיר ספירה. מסמך שהאימות שלו נכשל
    # (residuals=None + error) אינו נבדק, ואסור שייספר כאילו עבר.
    verified_docs = [x for x in summary_docs
                     if isinstance((x["verification"] or {}).get("residuals"), int)]
    failed_docs = [x for x in summary_docs
                   if x["verification"] is not None and x not in verified_docs]
    total_residuals = sum(x["verification"]["residuals"] for x in verified_docs)
    summary = {
        "out_dir": out_dir,
        "engine_requested": args.engine,
        "engine_used": map_engine,
        "gemma_available": gemma_ok,
        "burned": burned,
        "documents": summary_docs,
        "totals": {
            "documents": len(summary_docs),
            "redactions": sum(x["total"] for x in summary_docs),
            "verified_documents": len(verified_docs),
            "verification_errors": len(failed_docs),
            "residuals": total_residuals if burned else None,
        },
    }
    with open(os.path.join(out_dir, "redaction_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    _print_summary(summary)


def _print_summary(summary):
    print("== סיכום השחרה ==")
    print(f"מנוע: {summary['engine_used']} (התבקש {summary['engine_requested']}, "
          f"Gemma זמין: {summary['gemma_available']}) | נצרב: {summary['burned']}\n")
    print(f"{'#':>3}  {'מלבנים':>6}  {'עמ׳':>4}  קובץ")
    for i, d in enumerate(summary["documents"], 1):
        print(f"{i:>3}  {d['total']:>6}  {d['pages_with_redactions']:>4}  {d['filename']}")
        if d["by_category"]:
            by = ", ".join(f"{k}:{v}" for k, v in d["by_category"].items())
            print(f"       ({by})")
    print(f"\nסה\"כ {summary['totals']['redactions']} מלבנים ב-{summary['totals']['documents']} מסמכים.")
    if not summary["burned"]:
        print("שער אנושי: פתח את review_preview.pdf בכל מסמך, סקור, ואז הרץ שוב עם --burn.")
    else:
        res = summary["totals"]["residuals"]
        print(f"\nאימות שאריות: {summary['totals']['verified_documents']}/"
              f"{summary['totals']['documents']} מסמכים נבדקו, {res} שאריות אפשריות.")
        if res:
            for d in summary["documents"]:
                v = d.get("verification") or {}
                if v.get("residuals"):
                    pages = ", ".join(str(p) for p in v.get("pages", []))
                    print(f"  [!] {d['filename']}: {v['residuals']} שאריות בעמודים {pages}")
            print("אימות נכשל. אל תעביר את הקבצים החוצה לפני בדיקה ידנית.")
        if summary["totals"]["verification_errors"]:
            print(f"  [!] {summary['totals']['verification_errors']} מסמכים "
                  f"שהאימות שלהם נכשל: לא נבדקו, לא 'עברו'.")
        print("קובצי <שם>.redacted.pdf נשמרו לצד המקור. אמת ויזואלית לפני העלאה חיצונית.")


if __name__ == "__main__":
    main()
