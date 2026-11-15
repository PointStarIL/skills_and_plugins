#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Full-read coverage gate for case documents (מזקק השאלות לנבו).

Every document is split into units (a PDF page, or a ~3,500-character slice of a
Word or text file). Claude may read units ONLY through `show`, which prints the
full text of the units between two halves of a one-time code: half A at the top,
half B at the bottom. A unit counts as read only after `confirm A B`, which is
possible only if the whole output reached Claude (a cut-off output loses half B,
a tail-only output loses half A). A page with no text layer (a scan) is read with
Claude's own vision and recorded with `vision`. `gate` passes only when every
unit of every document is read. There is no partial pass.

Guarantees (each has a negative case in --selftest):
 1. gate fails while any unit is unread.
 2. confirm with a wrong code marks nothing.
 3. a show request larger than the output limit is refused.
 4. a vision record that is too short is refused, and vision is refused for a
    unit that has a text layer.
 5. a code can be used once.

Usage:
  python coverage.py scan <file-or-folder> [...]
  python coverage.py show <doc> <from> <to>
  python coverage.py confirm <codeA> <codeB>
  python coverage.py vision <doc> <unit> --text "<what the page says>"
  python coverage.py status
  python coverage.py gate
  python coverage.py --selftest
State: ./_coverage/ledger.json (override with env COVERAGE_DIR).
"""
import json, os, re, secrets, sys, zipfile, tempfile, shutil
from html import unescape

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

UNIT_CHARS = 3500          # slice size for Word / text files
SHOW_LIMIT = 24000         # max characters printed by one show call
SCAN_MIN_CHARS = 40        # a PDF page with less text than this is a scan
VISION_MIN_CHARS = 30      # a vision record must be at least this long
EXTS = {".pdf", ".docx", ".txt", ".md", ".png", ".jpg", ".jpeg"}


def state_dir():
    return os.environ.get("COVERAGE_DIR") or os.path.join(os.getcwd(), "_coverage")


def load():
    p = os.path.join(state_dir(), "ledger.json")
    if not os.path.exists(p):
        die("אין עדיין רישום. מריצים קודם: coverage.py scan <קבצי התיק>")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(led):
    d = state_dir()
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, "ledger.json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(led, f, ensure_ascii=False, indent=1)
    os.replace(tmp, os.path.join(d, "ledger.json"))


def die(msg, code=2):
    print(msg)
    sys.exit(code)


# ---------- extraction ----------

def pdf_pages(path):
    try:
        from pypdf import PdfReader
        return [(p.extract_text() or "") for p in PdfReader(path).pages]
    except ImportError:
        pass
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            return [(p.extract_text() or "") for p in pdf.pages]
    except ImportError:
        die("אין כלי לקריאת PDF בסביבה (pypdf או pdfplumber). אי אפשר להמשיך בלי קריאה מלאה.")


def docx_text(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    paras = []
    for p in re.findall(r"<w:p[ >].*?</w:p>", xml, flags=re.S):
        t = "".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", p, flags=re.S))
        paras.append(unescape(t))
    return "\n".join(paras)


def slice_text(text):
    marks = list(re.finditer(r"^=+\s*עמוד\s+\d+\s*=+\s*$", text, flags=re.M))
    if marks:
        parts = [text[m.start():(marks[i + 1].start() if i + 1 < len(marks) else len(text))]
                 for i, m in enumerate(marks)]
        head = text[:marks[0].start()].strip()
        if head:
            parts[0] = head + "\n" + parts[0]
        return [p.strip() for p in parts if p.strip()]
    units, cur = [], ""
    for para in text.split("\n"):
        if len(cur) + len(para) + 1 > UNIT_CHARS and cur:
            units.append(cur)
            cur = ""
        while len(para) > UNIT_CHARS:
            units.append(para[:UNIT_CHARS])
            para = para[UNIT_CHARS:]
        cur += para + "\n"
    if cur.strip():
        units.append(cur)
    return units or [""]


def extract(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        units = []
        for t in pdf_pages(path):
            kind = "text" if len(t.strip()) >= SCAN_MIN_CHARS else "vision"
            units.append({"kind": kind, "text": t})
        return units
    if ext == ".docx":
        return [{"kind": "text", "text": u} for u in slice_text(docx_text(path))]
    if ext in (".txt", ".md"):
        with open(path, encoding="utf-8", errors="replace") as f:
            return [{"kind": "text", "text": u} for u in slice_text(f.read())]
    if ext in (".png", ".jpg", ".jpeg"):
        return [{"kind": "vision", "text": ""}]
    return None


# ---------- commands ----------

def cmd_scan(paths):
    files = []
    for p in paths:
        if os.path.isdir(p):
            for root, _, names in os.walk(p):
                if os.path.basename(root) == "_coverage":
                    continue
                for n in sorted(names):
                    files.append(os.path.join(root, n))
        elif os.path.exists(p):
            files.append(p)
        else:
            die(f"הקובץ לא נמצא: {p}")
    docs, skipped = [], []
    for f in files:
        if os.path.splitext(f)[1].lower() not in EXTS:
            skipped.append(os.path.basename(f))
            continue
        units = extract(f)
        doc_id = f"d{len(docs) + 1}"
        docs.append({"id": doc_id, "name": os.path.basename(f), "path": f,
                     "units": [{"n": i + 1, "kind": u["kind"], "text": u["text"], "read": None}
                               for i, u in enumerate(units)]})
    if not docs:
        die("לא נמצא אף מסמך לקריאה (PDF, Word, טקסט או תמונה).")
    save({"docs": docs, "pending": {}, "used": []})
    total = sum(len(d["units"]) for d in docs)
    vis = sum(1 for d in docs for u in d["units"] if u["kind"] == "vision")
    print(f"נרשמו {len(docs)} מסמכים, {total} יחידות קריאה. מתוכן {vis} סרוקות, ונקראות בעין.")
    for d in docs:
        v = sum(1 for u in d["units"] if u["kind"] == "vision")
        print(f"  {d['id']}  {d['name']}  ·  {len(d['units'])} יחידות" + (f" ({v} סרוקות)" if v else ""))
    if skipped:
        print("קבצים שאינם מסמך קריא ולא נרשמו: " + ", ".join(skipped))
        print("אם אחד מהם הוא מסמך של התיק, צריך להמיר אותו ל-PDF, Word או תמונה ולהריץ scan מחדש.")


def find_doc(led, doc_id):
    for d in led["docs"]:
        if d["id"] == doc_id:
            return d
    die(f"אין מסמך {doc_id}. רשימת המסמכים: coverage.py status")


def cmd_show(doc_id, a, b):
    led = load()
    d = find_doc(led, doc_id)
    a, b = int(a), int(b)
    if a < 1 or b > len(d["units"]) or a > b:
        die(f"טווח לא תקין. ב-{doc_id} יש {len(d['units'])} יחידות.")
    units = d["units"][a - 1:b]
    size = sum(len(u["text"]) for u in units)
    if size > SHOW_LIMIT and b > a:
        die(f"הטווח ארוך מדי לקריאה אחת ({size} תווים, המקסימום {SHOW_LIMIT}). מקצרים את הטווח.")
    code_a, code_b = secrets.token_hex(3), secrets.token_hex(3)
    led["pending"][code_a + code_b] = {"doc": doc_id, "units": [u["n"] for u in units if u["kind"] == "text"]}
    save(led)
    print(f"קוד פתיחה: {code_a}")
    for u in units:
        print(f"\n===== {d['name']} · יחידה {u['n']} מתוך {len(d['units'])} =====")
        if u["kind"] == "vision":
            print("[עמוד סרוק בלי שכבת טקסט. קוראים אותו בעין מהמסמך עצמו, ורושמים: coverage.py vision "
                  f"{doc_id} {u['n']} --text \"...\"]")
        else:
            print(u["text"])
    print(f"\nקוד סיום: {code_b}")
    print(f"אחרי קריאת כל הטקסט שלמעלה: coverage.py confirm {code_a} <קוד הסיום>")


def cmd_confirm(code_a, code_b):
    led = load()
    key = code_a + code_b
    if key in led["used"]:
        die("הקוד הזה כבר נוצל. כל קריאה מקבלת קוד חדש.")
    p = led["pending"].get(key)
    if not p:
        die("הקוד לא תואם. אם הפלט נחתך, מריצים show שוב על אותו טווח וקוראים אותו עד הסוף.")
    d = find_doc(led, p["doc"])
    for u in d["units"]:
        if u["n"] in p["units"]:
            u["read"] = u["read"] or "text"
    del led["pending"][key]
    led["used"].append(key)
    save(led)
    print(f"נרשמה קריאה של {len(p['units'])} יחידות ב-{d['name']}.")


def cmd_vision(doc_id, n, text):
    led = load()
    d = find_doc(led, doc_id)
    n = int(n)
    if n < 1 or n > len(d["units"]):
        die("מספר יחידה לא תקין.")
    u = d["units"][n - 1]
    if u["kind"] != "vision":
        die("ליחידה הזו יש שכבת טקסט. קוראים אותה עם show, לא בעין.")
    if len((text or "").strip()) < VISION_MIN_CHARS:
        die(f"הרישום קצר מדי. כותבים מה כתוב בעמוד (לפחות {VISION_MIN_CHARS} תווים).")
    u["read"] = "vision"
    u["text"] = text.strip()
    save(led)
    print(f"נרשמה קריאה בעין של {d['name']}, יחידה {n}.")


def counts(led):
    total = sum(len(d["units"]) for d in led["docs"])
    done = sum(1 for d in led["docs"] for u in d["units"] if u["read"])
    return total, done


def cmd_status():
    led = load()
    for d in led["docs"]:
        unread = [u["n"] for u in d["units"] if not u["read"]]
        state = "נקרא במלואו" if not unread else "לא נקראו: " + ranges(unread)
        print(f"{d['id']}  {d['name']}  ·  {len(d['units'])} יחידות  ·  {state}")
    t, r = counts(led)
    print(f"סה\"כ: נקראו {r} מתוך {t} יחידות.")


def ranges(nums):
    out, s, prev = [], None, None
    for x in nums + [None]:
        if s is None:
            s = prev = x
        elif x is not None and x == prev + 1:
            prev = x
        else:
            out.append(f"{s}" if s == prev else f"{s}-{prev}")
            s = prev = x
    return ", ".join(out)


def cmd_gate():
    led = load()
    t, r = counts(led)
    if r == t:
        print(f"PASS · נקראו {len(led['docs'])} מתוך {len(led['docs'])} מסמכים, {t} מתוך {t} יחידות. קריאה מלאה.")
        return 0
    print(f"BLOCK · נקראו {r} מתוך {t} יחידות. אי אפשר להמשיך לפני קריאה מלאה.")
    for d in led["docs"]:
        unread = [u["n"] for u in d["units"] if not u["read"]]
        if unread:
            print(f"  {d['id']}  {d['name']}: חסרות יחידות {ranges(unread)}")
    return 2


# ---------- selftest ----------

def selftest():
    import io, contextlib
    tmp = tempfile.mkdtemp()
    os.environ["COVERAGE_DIR"] = os.path.join(tmp, "_coverage")
    ok = 0

    def run(fn, *a):
        buf = io.StringIO()
        code = 0
        with contextlib.redirect_stdout(buf):
            try:
                rv = fn(*a)
                code = rv if isinstance(rv, int) else 0
            except SystemExit as e:
                code = e.code or 0
        return code, buf.getvalue()

    try:
        doc = os.path.join(tmp, "a.txt")
        with open(doc, "w", encoding="utf-8") as f:
            f.write("=== עמוד 1 ===\nשורה ראשונה בעמוד הראשון\n=== עמוד 2 ===\nשורה שנייה בעמוד השני\n")
        big = os.path.join(tmp, "b.txt")
        with open(big, "w", encoding="utf-8") as f:
            f.write(("מילה " * 900 + "\n") * 40)
        img = os.path.join(tmp, "c.png")
        open(img, "wb").close()
        c, out = run(cmd_scan, [doc, big, img])
        assert c == 0 and "נרשמו 3 מסמכים" in out, out
        ok += 1
        # 1. gate fails before reading
        c, out = run(cmd_gate)
        assert c == 2 and "BLOCK" in out, "NEG: gate must block while units are unread"
        ok += 1
        # read d1 fully
        c, out = run(cmd_show, "d1", "1", "2")
        code_a = re.search(r"קוד פתיחה: (\w+)", out).group(1)
        code_b = re.search(r"קוד סיום: (\w+)", out).group(1)
        # 2. wrong code marks nothing
        c, out = run(cmd_confirm, code_a, "000000")
        assert c == 2, "NEG: a wrong closing code must be refused"
        c, out = run(cmd_status)
        assert "לא נקראו: 1-2" in out, out
        ok += 1
        c, out = run(cmd_confirm, code_a, code_b)
        assert c == 0, out
        # 5. code used once
        c, out = run(cmd_confirm, code_a, code_b)
        assert c == 2 and "כבר נוצל" in out, "NEG: a code must not be reusable"
        ok += 1
        # 3. oversize show refused
        n_big = len(load()["docs"][1]["units"])
        c, out = run(cmd_show, "d2", "1", str(n_big))
        assert c == 2 and "ארוך מדי" in out, "NEG: an oversize show must be refused"
        ok += 1
        # 4. vision rules
        c, out = run(cmd_vision, "d3", "1", "קצר")
        assert c == 2, "NEG: a too-short vision record must be refused"
        c, out = run(cmd_vision, "d1", "1", "טקסט ארוך מספיק כדי לעבור את הסף של שלושים תווים")
        assert c == 2, "NEG: vision must be refused for a unit with a text layer"
        c, out = run(cmd_vision, "d3", "1", "תמונה של חשבונית: סכום, תאריך ושם הספק, כפי שנראים בעמוד")
        assert c == 0, out
        ok += 1
        # still blocked: d2 unread
        c, out = run(cmd_gate)
        assert c == 2 and "d2" in out, "NEG: gate must block while one document is unread"
        ok += 1
        # read d2 in allowed ranges
        led = load()
        units = led["docs"][1]["units"]
        i = 1
        while i <= len(units):
            j, size = i, 0
            while j <= len(units) and size + len(units[j - 1]["text"]) <= SHOW_LIMIT:
                size += len(units[j - 1]["text"])
                j += 1
            c, out = run(cmd_show, "d2", str(i), str(max(i, j - 1)))
            ca = re.search(r"קוד פתיחה: (\w+)", out).group(1)
            cb = re.search(r"קוד סיום: (\w+)", out).group(1)
            run(cmd_confirm, ca, cb)
            i = max(i, j - 1) + 1
        c, out = run(cmd_gate)
        assert c == 0 and "PASS" in out, out
        ok += 1
        print(f"SELFTEST PASS ({ok}/8)")
        return 0
    except AssertionError as e:
        print(f"SELFTEST FAIL ({ok}/8): {e}")
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "--selftest":
        return selftest()
    if cmd == "scan" and rest:
        cmd_scan(rest); return 0
    if cmd == "show" and len(rest) == 3:
        cmd_show(*rest); return 0
    if cmd == "confirm" and len(rest) == 2:
        cmd_confirm(*rest); return 0
    if cmd == "vision" and len(rest) >= 2:
        text = None
        if "--text" in rest:
            text = rest[rest.index("--text") + 1] if rest.index("--text") + 1 < len(rest) else ""
        cmd_vision(rest[0], rest[1], text); return 0
    if cmd == "status":
        cmd_status(); return 0
    if cmd == "gate":
        return cmd_gate()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
