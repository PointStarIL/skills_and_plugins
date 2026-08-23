#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wikilaw.py - חיבור ישיר ל"ספר החוקים הפתוח" בוויקיטקסט העברי.
מאפשר חיפוש חוקים ותקנות, שליפת תוכן עניינים, ושליפת נוסח מדויק של סעיף.

כל הפלט הוא נוסח מילה-במילה מוויקיטקסט, עם מראה מקום ותאריך גרסה.
"""
import argparse, json, os, re, sys, time, urllib.parse, urllib.request

__version__ = "1.0.0"

API = "https://he.wikisource.org/w/api.php"
RAW = "https://he.wikisource.org/w/index.php"
UA = "MarcusLawWikisourceTool/1.0 (legal research; contact: chaim@marcus-law.co.il)"
CACHE_DIR = os.environ.get("WIKILAW_CACHE", os.path.expanduser("~/.wikilaw-cache"))
CACHE_TTL = int(os.environ.get("WIKILAW_TTL", 60 * 60 * 24 * 7))  # שבוע


# ---------------------------------------------------------------- HTTP

def _get(url, params=None, tries=6):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept-Encoding": "identity",
            })
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # rate limit / network
            last = e
            time.sleep(min(30, 3 * (2 ** i)))
    raise SystemExit("שגיאת רשת מול ויקיטקסט: %s" % last)


def api(**params):
    params.setdefault("format", "json")
    params.setdefault("formatversion", "2")
    return json.loads(_get(API, params))


# ---------------------------------------------------------------- cache

def _cache_path(title):
    safe = re.sub(r"[^\w֐-׿]+", "_", title)[:120]
    return os.path.join(CACHE_DIR, safe + ".json")


def fetch_page(title, refresh=False):
    """מחזיר dict: title, wikitext, revid, timestamp, url"""
    p = _cache_path(title)
    if not refresh and os.path.exists(p) and (time.time() - os.path.getmtime(p)) < CACHE_TTL:
        try:
            with open(p, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            pass
    d = api(action="query", prop="revisions", titles=title,
            rvprop="content|timestamp|ids", rvslots="main", redirects="1")
    pages = d.get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        raise SystemExit("לא נמצא דף בשם: %s\nנסה: wikilaw.py search \"%s\"" % (title, title))
    pg = pages[0]
    rev = pg["revisions"][0]
    out = {
        "title": pg["title"],
        "wikitext": rev["slots"]["main"]["content"],
        "revid": rev.get("revid"),
        "timestamp": rev.get("timestamp"),
        "url": "https://he.wikisource.org/wiki/" + urllib.parse.quote(pg["title"].replace(" ", "_")),
    }
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False)
    return out


# ---------------------------------------------------- rendering wikitext

DROP = {"ח:התחלה", "ח:סוף", "ח:סוגר", "ח:מפריד", "ח:פתיח-התחלה", "ח:פתיח-סוף",
        "ח:מבוא", "ח:חתימות", "ח:מאגר", "ח:סוף-טור", "ח:טור"}
LEVEL = {"ח:תת": 1, "ח:תתת": 2, "ח:תתתת": 3, "ח:תתתתת": 4, "ח:תתתתתת": 5}


def _split_args(body):
    """מפצל ארגומנטים של תבנית לפי | ברמה העליונה בלבד."""
    parts, depth, cur = [], 0, ""
    i = 0
    while i < len(body):
        c = body[i]
        if body.startswith("{{", i) or body.startswith("[[", i):
            depth += 1; cur += body[i:i+2]; i += 2; continue
        if body.startswith("}}", i) or body.startswith("]]", i):
            depth -= 1; cur += body[i:i+2]; i += 2; continue
        if c == "|" and depth == 0:
            parts.append(cur); cur = ""; i += 1; continue
        cur += c; i += 1
    parts.append(cur)
    return parts


def _render_template(name, args, kw):
    n = name.strip()
    if n in DROP:
        return ""
    if n == "ח:כותרת":
        return args[0] if args else ""
    if n in ("ח:קטע2", "ח:קטע3", "ח:קטע4", "ח:קטע5"):
        return args[1] if len(args) > 1 else (args[0] if args else "")
    if n in ("ח:סעיף", "ח:סעיף*"):
        num = args[0].strip() if args else ""
        ttl = args[1].strip() if len(args) > 1 else ""
        tik = args[2].strip() if len(args) > 2 else ""
        head = (num + ". " if num else "") + ttl
        if tik:
            head += "   [" + tik + "]"
        return head.strip()
    if n in LEVEL:
        # תבנית סעיף-משנה עשויה לשאת יותר מסמן אחד: {{ח:תת|(ד)|(1)}}.
        # כל הסמנים נשמרים, אחרת הפלט מאבד את מספר הפסקה.
        marks = " ".join(a.strip() for a in args if a.strip())
        return " " * LEVEL[n] + marks + " "
    if n == "ח:ת":
        return ""
    if n in ("ח:פנימי", "ח:חיצוני"):
        return args[-1] if args else ""
    if n == "ח:תיבה":
        return args[0] if args else ""
    if n == "ח:הערה":
        t = (args[0] if args else "").strip()
        return t if (t.startswith("(") and t.endswith(")")) else "(" + t + ")"
    if n.startswith("ח:"):
        return " ".join(a for a in args if a)
    return " ".join(a for a in args if a)


def render(text):
    """ממיר wikitext של ספר החוקים לטקסט קריא, בלי לשנות מילים."""
    out, i = "", 0
    while i < len(text):
        if text.startswith("{{", i):
            depth, j = 1, i + 2
            while j < len(text) and depth:
                if text.startswith("{{", j):
                    depth += 1; j += 2
                elif text.startswith("}}", j):
                    depth -= 1; j += 2
                else:
                    j += 1
            body = text[i+2:j-2]
            parts = _split_args(body)
            name = parts[0]
            args, kw = [], {}
            for p in parts[1:]:
                m = re.match(r"^([\w֐-׿\- ]+)=(.*)$", p, re.S)
                if m:
                    kw[m.group(1).strip()] = render(m.group(2))
                else:
                    args.append(render(p))
            out += _render_template(name, args, kw)
            i = j
            continue
        if text.startswith("[[", i):
            j = text.find("]]", i)
            if j < 0:
                out += text[i]; i += 1; continue
            inner = text[i+2:j]
            out += inner.split("|")[-1]
            i = j + 2
            continue
        out += text[i]; i += 1
    out = re.sub(r"'''(.+?)'''", r"\1", out, flags=re.S)
    out = re.sub(r"''(.+?)''", r"\1", out, flags=re.S)
    out = re.sub(r"<[^>\n]{0,80}>", "", out)
    out = re.sub(r"[ \t]+\n", "\n", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


# ------------------------------------------------------------- structure

BLOCK_RE = re.compile(r"^\{\{(ח:סעיף\*?|ח:קטע[2-5])\|?")


def parse_structure(wikitext):
    """מחזיר רשימת בלוקים: כותרות פרקים/סימנים וסעיפים, עם גוף מלא."""
    lines = wikitext.split("\n")
    blocks, cur = [], None
    for idx, line in enumerate(lines):
        m = BLOCK_RE.match(line)
        if m:
            if cur:
                cur["end"] = idx
                blocks.append(cur)
            name = m.group(1)
            # פירוק ארגומנטים של השורה הפותחת
            depth, j = 1, 2
            while j < len(line) and depth:
                if line.startswith("{{", j): depth += 1; j += 2
                elif line.startswith("}}", j): depth -= 1; j += 2
                else: j += 1
            parts = _split_args(line[2:j-2])
            pos = [p for p in parts[1:] if not re.match(r"^[\w֐-׿\- ]+=", p)]
            if name.startswith("ח:קטע"):
                cur = {"kind": "heading", "level": int(name[-1]),
                       "anchor": pos[0].strip() if pos else "",
                       "title": render(pos[1]) if len(pos) > 1 else "",
                       "start": idx}
            else:
                cur = {"kind": "section",
                       "num": pos[0].strip() if pos else "",
                       "title": render(pos[1]) if len(pos) > 1 else "",
                       "amend": render(pos[2]) if len(pos) > 2 else "",
                       "start": idx}
            continue
        if cur is None:
            continue
    if cur:
        cur["end"] = len(lines)
        blocks.append(cur)
    for b in blocks:
        b["wikitext"] = "\n".join(lines[b["start"]:b["end"]])
    return blocks


def norm_num(s):
    s = (s or "").strip()
    s = s.replace("׳", "'").replace("״", '"')
    s = re.sub(r"[\s.]+$", "", s)
    return s


def source_line(pg, anchor=None):
    u = pg["url"] + ("#" + urllib.parse.quote(anchor.replace(" ", "_")) if anchor else "")
    ts = (pg.get("timestamp") or "")[:10]
    return "מקור: %s | ויקיטקסט, גרסה מיום %s (revid %s)" % (u, ts, pg.get("revid"))


# --------------------------------------------------------------- commands

def cmd_search(a):
    srsearch = a.query
    d = api(action="query", list="search", srsearch=srsearch,
            srlimit=a.limit, srnamespace=0)
    res = d.get("query", {}).get("search", [])
    if not res:
        print("לא נמצאו תוצאות עבור: %s" % srsearch); return
    print("נמצאו %d דפים (מוצגים %d):\n" % (d["query"]["searchinfo"]["totalhits"], len(res)))
    for r in res:
        snip = re.sub(r"<[^>]+>", "", r.get("snippet", ""))
        url = "https://he.wikisource.org/wiki/" + urllib.parse.quote(r["title"].replace(" ", "_"))
        print("• %s\n  %s\n  %s\n" % (r["title"], snip, url))


def cmd_toc(a):
    pg = fetch_page(a.title, a.refresh)
    blocks = parse_structure(pg["wikitext"])
    print("== %s ==" % pg["title"])
    print(source_line(pg)); print()
    for b in blocks:
        if b["kind"] == "heading":
            if not b["title"]:
                continue
            print("  " * (b["level"] - 2) + b["title"])
        elif a.sections:
            print("  " * 3 + "%s. %s" % (b["num"], b["title"]))


def cmd_sec(a):
    pg = fetch_page(a.title, a.refresh)
    blocks = parse_structure(pg["wikitext"])
    want = norm_num(a.num)
    hits = [b for b in blocks if b["kind"] == "section" and norm_num(b["num"]) == want]
    if not hits:
        digits = re.match(r"\d+", want)
        pref = digits.group(0) if digits else want[:2]
        near = [b["num"] for b in blocks if b["kind"] == "section"
                and norm_num(b["num"]).startswith(pref)]
        if not near:
            near = [b["num"] for b in blocks if b["kind"] == "section"
                    and norm_num(b["num"]).startswith(pref[:2])]
        print("לא נמצא סעיף %s בדף %s." % (a.num, pg["title"]))
        if near:
            print("סעיפים קרובים: %s" % ", ".join(near[:30]))
        return
    for b in hits:
        ctx = _context(blocks, b)
        print("== %s ==" % pg["title"])
        if ctx:
            print(" > ".join(ctx))
        print()
        if a.raw:
            print(b["wikitext"])
        else:
            print(render(b["wikitext"]))
        print()
        print(source_line(pg, "סעיף " + b["num"]))


def _context(blocks, target):
    ctx, cur = [], {}
    for b in blocks:
        if b is target:
            break
        if b["kind"] == "heading" and b["title"]:
            cur[b["level"]] = b["title"]
            for k in list(cur):
                if k > b["level"]:
                    del cur[k]
    return [cur[k] for k in sorted(cur)]


def cmd_grep(a):
    pg = fetch_page(a.title, a.refresh)
    blocks = parse_structure(pg["wikitext"])
    rx = re.compile(a.pattern)
    n = 0
    for b in blocks:
        if b["kind"] != "section":
            continue
        txt = render(b["wikitext"])
        if not rx.search(txt):
            continue
        n += 1
        print("── סעיף %s: %s ──" % (b["num"], b["title"]))
        if a.full:
            print(txt)
        else:
            for line in txt.split("\n"):
                if rx.search(line):
                    print("   " + line.strip())
        print()
        if n >= a.limit:
            print("(הופסק לאחר %d סעיפים; אפשר להעלות עם --limit)" % a.limit)
            break
    if not n:
        print("לא נמצאו סעיפים התואמים ל-%s בדף %s" % (a.pattern, pg["title"]))
        return
    print(source_line(pg))


def cmd_fulltext(a):
    q = 'insource:"%s"' % a.phrase
    d = api(action="query", list="search", srsearch=q, srlimit=a.limit, srnamespace=0)
    res = d.get("query", {}).get("search", [])
    print("חיפוש נוסח מדויק בכל ספר החוקים: \"%s\" — %d דפים\n"
          % (a.phrase, d["query"]["searchinfo"]["totalhits"]))
    for r in res:
        url = "https://he.wikisource.org/wiki/" + urllib.parse.quote(r["title"].replace(" ", "_"))
        print("• %s\n  %s\n" % (r["title"], url))


def cmd_text(a):
    pg = fetch_page(a.title, a.refresh)
    t = render(pg["wikitext"]) if not a.raw else pg["wikitext"]
    print("== %s ==" % pg["title"])
    print(source_line(pg)); print()
    print(t)


def main():
    p = argparse.ArgumentParser(description="ספר החוקים הפתוח — ויקיטקסט")
    p.add_argument("-V", "--version", action="version",
                   version="wikilaw.py %s" % __version__)
    sp = p.add_subparsers(dest="cmd", required=True)

    s = sp.add_parser("search", help="חיפוש חוק/תקנה לפי שם או נושא")
    s.add_argument("query"); s.add_argument("--limit", type=int, default=10)
    s.set_defaults(func=cmd_search)

    s = sp.add_parser("toc", help="תוכן עניינים של חוק")
    s.add_argument("title"); s.add_argument("--sections", action="store_true")
    s.add_argument("--refresh", action="store_true"); s.set_defaults(func=cmd_toc)

    s = sp.add_parser("sec", help="שליפת נוסח סעיף מדויק")
    s.add_argument("title"); s.add_argument("num")
    s.add_argument("--raw", action="store_true")
    s.add_argument("--refresh", action="store_true"); s.set_defaults(func=cmd_sec)

    s = sp.add_parser("grep", help="חיפוש ביטוי בתוך חוק, לפי סעיפים")
    s.add_argument("title"); s.add_argument("pattern")
    s.add_argument("--full", action="store_true")
    s.add_argument("--limit", type=int, default=15)
    s.add_argument("--refresh", action="store_true"); s.set_defaults(func=cmd_grep)

    s = sp.add_parser("fulltext", help="חיפוש נוסח מדויק בכל ספר החוקים")
    s.add_argument("phrase"); s.add_argument("--limit", type=int, default=15)
    s.set_defaults(func=cmd_fulltext)

    s = sp.add_parser("text", help="נוסח מלא של דף (זהירות: חוקים גדולים)")
    s.add_argument("title"); s.add_argument("--raw", action="store_true")
    s.add_argument("--refresh", action="store_true"); s.set_defaults(func=cmd_text)

    a = p.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
