#!/usr/bin/env python3
"""
Text sanitiser for legal pleading packages.

Why this exists:
LLM-generated text is often given away by typographic markers that human
typists rarely produce on a Hebrew Word document — most prominently the em
dash (U+2014, '—'). Court-ready filings should match the look-and-feel of a
human-typed document, so the build-appendix-pdf skill enforces a hard
ban on em dashes (and en dashes) anywhere it places text into the final PDF:
TOC headers, TOC rows, cover-page names, bookmarks, and metadata.

Public API:
    sanitize(text)              -> str   replace banned dashes
    assert_no_em_dash(text, ctx) -> None  raise if any banned dash present
    sanitize_appendix_list(items) -> list (deep copy with sanitized names/labels)
"""

from typing import List, Dict, Any

# Characters that betray AI authorship in a Hebrew legal document
BANNED_DASHES = {
    '—': '-',      # U+2014 em dash      → hyphen-minus
    '–': '-',      # U+2013 en dash      → hyphen-minus
    '―': '-',      # U+2015 horizontal bar
    '‒': '-',      # U+2012 figure dash
    '⸻': '-',     # U+2E3B three-em dash
    '⸺': '-',     # U+2E3A two-em dash
}

# Other typographic giveaways often produced by AI / LibreOffice autocorrect
BANNED_QUOTES = {
    '‘': "'",   # left single quote
    '’': "'",   # right single quote
    '“': '"',   # left double quote
    '”': '"',   # right double quote
}


def sanitize(text: str, *, replace_quotes: bool = False) -> str:
    """
    Replace banned dashes (and optionally banned smart quotes) with their
    plain ASCII equivalents.

    Args:
        text: Input string.
        replace_quotes: If True, also replace curly quotes with straight quotes.

    Returns:
        Sanitised string. Returns input unchanged if not a str.
    """
    if not isinstance(text, str):
        return text
    out = text
    for bad, good in BANNED_DASHES.items():
        if bad in out:
            out = out.replace(bad, good)
    if replace_quotes:
        for bad, good in BANNED_QUOTES.items():
            if bad in out:
                out = out.replace(bad, good)
    return out


def assert_no_em_dash(text: str, context: str = "") -> None:
    """
    Raise ValueError if any banned dash appears in the text.

    Use this on user-supplied text BEFORE rendering to TOC/cover/bookmark.
    """
    if not isinstance(text, str):
        return
    for bad in BANNED_DASHES:
        if bad in text:
            raise ValueError(
                f"Banned dash {bad!r} (U+{ord(bad):04X}) detected in {context!r}: "
                f"{text!r}. Use a regular hyphen '-' instead."
            )


def sanitize_appendix_list(appendix_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Return a deep-copied list with all string fields sanitised.

    Sanitises: name, label, id, and any other string-valued field.
    """
    out = []
    for item in appendix_list:
        clean = {}
        for k, v in item.items():
            clean[k] = sanitize(v) if isinstance(v, str) else v
        out.append(clean)
    return out


if __name__ == '__main__':
    # quick self-test
    bad = 'תעודת תואר ראשון (B.A.) — פקולטה לחינוך'
    good = sanitize(bad)
    print(f"in:  {bad!r}")
    print(f"out: {good!r}")
    assert '—' not in good
    print("✓ self-test passed")
