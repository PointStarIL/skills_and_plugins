#!/usr/bin/env python3
"""בדיקת תמציתיות לטיוטת החלטה, לפי references/chair-style.md.

שימוש: python3 check_concision.py <טיוטה.docx> [--terms "מונח1,מונח2"]

מדווח על פרק "דיון והכרעה" (עד "סוף דבר"):
  * אורך במילים, בלי ציטוטי בלוק
  * מספר כותרות משנה
  * ביטויי מפת דרכים, "איננו נדרשים", מסקנות ביניים, הסתייגות ממקורות, הודאה בטענה שכנגד
  * מופעי "לעיל" ו"אכן" מחוץ לציטוטים
  * פסקאות שנפתחות בחזרה על טענת צד
  * מונחי מפתח שמופיעים ביותר מגוש אחד (נושא שנפתח, נסגר ונפתח שוב)
קוד יציאה 1 אם חרגנו מסף כלשהו. הסקריפט מצביע איפה לבדוק; הוא לא מחליף קריאה.
"""
import re
import sys
import argparse

try:
    import docx
except ImportError:
    sys.exit("נדרש python-docx: pip install python-docx")

ROADMAP = ["נקדים", "ונפרט;", "בטרם נפנה", "נפנה עתה", "נזכיר כי", "מן הכלל אל הפרט",
           "כפי שנפרט להלן", "נדון גם בכל אחת"]
NOT_DECIDING = ["איננו נדרשים", "אין צורך להכריע", "איננו קובעים מסמרות", "למעלה מן הצורך",
                "אין אנו נדרשים", "לא נקבע מסמרות"]
INTERIM = ["מצטרף למסקנתנו", "אף מטעם זה", "גם בכך יש תמיכה", "מחזקת את מסקנתנו",
           "מסקנתנו עומדת בעינה", "מצטרפת לתמונה", "מצטרף לתמונה"]
SOURCE_HEDGE = ["אין זו הלכה", "ולא הלכה", "אינו הלכה", "אינו פסק דין", "מעמדו של המסמך",
                "נאמרו אמנם למעלה"]
CONCEDE = ["אינה מבוטלת", "יש משקל של ממש", "יש ממש בחלק", "אכן, המליאה", "אכן, איננו מתעלמים"]
GENERIC = {"עניין זה", "עניין הסעיף", "עניין הצורך"}
RESTATE = re.compile(r"^(העוררת טוענת|המשיבות טוענות|המועצה טוענת|הוועדה המקומית טוענת|לטענת |"
                     r"המשיבות מבקשות|המועצה מבקשת|העוררת מבקשת)")

LIMITS = {"words": 4000, "headings": 3, "roadmap": 0, "not_deciding": 1, "interim": 1,
          "source_hedge": 0, "concede": 0, "leil": 3, "achen": 3, "restate": 2, "scattered": 2}


def is_heading(p):
    s = p.style.name if p.style is not None else ""
    return s.startswith("Heading") or s in ("2", "3", "Title")


def is_quote(p):
    s = p.style.name if p.style is not None else ""
    return s in ("Quote", "a9") or s.lower().startswith("quote")


def section(doc):
    paras, on = [], False
    for p in doc.paragraphs:
        t = p.text.strip()
        if is_heading(p) and "דיון והכרעה" in t:
            on = True
            continue
        if on and is_heading(p) and "סוף דבר" in t:
            break
        if on:
            paras.append(p)
    return paras


def hits(texts, phrases):
    out = []
    for i, t in texts:
        for ph in phrases:
            if ph in t:
                out.append((i, ph))
    return out


def scattered(texts, terms, gap=4):
    """מונח שמופיע בשני גושים או יותר, שביניהם יותר מ-gap פסקאות."""
    res = {}
    for term in terms:
        idx = [i for i, t in texts if term in t]
        if len(idx) < 2:
            continue
        clusters = [[idx[0]]]
        for j in idx[1:]:
            if j - clusters[-1][-1] > gap:
                clusters.append([j])
            else:
                clusters[-1].append(j)
        if len(clusters) > 1:
            res[term] = [c[0] for c in clusters]
    return res


def auto_terms(texts):
    found = set()
    for _, t in texts:
        found.update(re.findall(r"סעיף \d+(?:\.\d+)*[א-ת]?(?:\([^)]{1,4}\))*", t))
        found.update(re.findall(r"התכנית הכוללנית|תנאי \d+|\d+ עד \d+ בקשות", t))
        found.update(m for m in re.findall(r"עניין [א-ת\"']{3,}", t) if m not in GENERIC)
    # סעיפי מסגרת שמופיעים לאורך כל ההחלטה באופן טבעי
    return sorted(x for x in found if x not in ("סעיף 62", "סעיף 62א", "סעיף 62א(א)"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("docx")
    ap.add_argument("--terms", default="")
    a = ap.parse_args()
    doc = docx.Document(a.docx)
    sec = section(doc)
    if not sec:
        sys.exit('לא נמצאה כותרת "דיון והכרעה"')
    body = [(i, p.text.strip()) for i, p in enumerate(sec) if p.text.strip() and not is_heading(p) and not is_quote(p)]
    headings = [p.text.strip() for p in sec if is_heading(p) and p.text.strip()]
    words = sum(len(t.split()) for _, t in body)
    terms = [x.strip() for x in a.terms.split(",") if x.strip()] or auto_terms(body)
    r = {
        "words": words,
        "headings": len(headings),
        "roadmap": hits(body, ROADMAP),
        "not_deciding": hits(body, NOT_DECIDING),
        "interim": hits(body, INTERIM),
        "source_hedge": hits(body, SOURCE_HEDGE),
        "concede": hits(body, CONCEDE),
        "leil": [(i, "לעיל") for i, t in body for _ in re.findall(r"לעיל", t)],
        "achen": [(i, "אכן") for i, t in body if re.search(r"(^|\s)אכן[ ,]", t)],
        "restate": [(i, t[:40]) for i, t in body if RESTATE.match(t)],
        "scattered": scattered(body, terms),
    }
    fail = False
    names = {"words": "מילים בפרק הדיון (בלי ציטוטים)", "headings": "כותרות משנה",
             "roadmap": "מפת דרכים/הקדמה", "not_deciding": "איננו נדרשים/למעלה מן הצורך",
             "interim": "מסקנת ביניים", "source_hedge": "הסתייגות ממשקל מקור",
             "concede": "הודאה בכוח טענה שכנגד", "leil": "לעיל", "achen": "אכן",
             "restate": "פסקה שנפתחת בחזרה על טענת צד", "scattered": "נושא בכמה גושים"}
    print(f"בדיקת תמציתיות: {a.docx}")
    for k, v in r.items():
        n = v if isinstance(v, int) else len(v)
        ok = n <= LIMITS[k]
        fail |= not ok
        print(f"{'✓' if ok else '✗'} {names[k]}: {n} (סף {LIMITS[k]})")
        if not isinstance(v, int) and not ok:
            items = v.items() if isinstance(v, dict) else v
            for it in list(items)[:12]:
                print(f"    {it}")
    if headings:
        print("  כותרות:", " | ".join(headings))
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
