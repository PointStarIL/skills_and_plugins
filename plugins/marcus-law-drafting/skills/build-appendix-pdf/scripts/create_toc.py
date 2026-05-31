#!/usr/bin/env python3
"""
Create Hebrew RTL Table of Contents page(s) for legal appendix package.

REWRITTEN: Uses WeasyPrint (HTML→PDF) instead of reportlab+bidi.
The previous reportlab+bidi approach physically reversed Hebrew glyphs
in the PDF byte stream, which caused text to render reversed in viewers
that did not honour bidi blocks. WeasyPrint relies on the system's
native HarfBuzz/Pango shaping pipeline, so RTL text is laid out
correctly with no manual reversal required.

Public API preserved:
    create_toc_pdf(toc_list, output_path, style='hebrew', format_mode='auto')
"""

import os
from typing import List, Dict, Any, Optional

try:
    from weasyprint import HTML, CSS
    HAS_WEASYPRINT = True
except ImportError:
    HAS_WEASYPRINT = False


_BASE_CSS = """
@page { size: A4; margin: 2.5cm; }
body { font-family: 'David', 'FrankRuehl CLM', 'DejaVu Sans', sans-serif;
       direction: rtl; text-align: right; color: #1a1a1a; margin: 0; }
* { box-sizing: border-box; }
h1 { background: #2C5F8A; color: #fff; padding: 14px 20px;
     font-size: 22px; margin: 0 0 24px 0; border-radius: 4px; }
table { width: 100%; border-collapse: collapse; direction: rtl; font-size: 14px; }
th { background: #2C5F8A; color: #fff; padding: 10px 12px;
     text-align: right; font-weight: bold; }
th.idx, th.pg { text-align: center; }
td { padding: 10px 12px; border-bottom: 1px solid #ddd; vertical-align: top; }
td.idx { width: 12%; text-align: center; font-weight: bold; }
td.name { text-align: right; }
td.pg { width: 18%; text-align: center; font-weight: bold; }
tr:nth-child(even) td { background: #F5F7FA; }
.simple td.name { width: 70%; }
"""


def _format_label(item: Dict[str, Any]) -> str:
    """Get the appendix label (e.g., 'נספח א'' or 'נספח 1')."""
    if 'label' in item and item['label']:
        return str(item['label'])
    return f"נספח {item.get('id', '?')}"


def _build_toc_html(toc_list: List[Dict[str, Any]],
                    style: str = 'hebrew',
                    format_mode: str = 'auto') -> str:
    """Build the TOC HTML string."""
    # Decide format
    n = len(toc_list)
    if format_mode == 'auto':
        format_mode = 'simple' if n <= 5 else 'full'

    # In simple mode: 2 columns (name, page)
    # In full mode: 3 columns (label, name, page)
    rows_html = []
    for item in toc_list:
        label = _format_label(item)
        name = str(item.get('name', ''))
        page = str(item.get('page', ''))
        if format_mode == 'simple':
            rows_html.append(
                f'<tr><td class="name">{label}: {name}</td>'
                f'<td class="pg">{page}</td></tr>'
            )
        else:
            rows_html.append(
                f'<tr><td class="idx">{item.get("id","")}</td>'
                f'<td class="name">{name}</td>'
                f'<td class="pg">{page}</td></tr>'
            )
    rows_str = '\n'.join(rows_html)

    if format_mode == 'simple':
        thead = ('<tr><th class="name">שם הנספח</th>'
                 '<th class="pg">עמוד</th></tr>')
        tclass = 'simple'
    else:
        thead = ('<tr><th class="idx">נספח</th>'
                 '<th class="name">שם הנספח</th>'
                 '<th class="pg">עמוד</th></tr>')
        tclass = 'full'

    return f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head><meta charset="utf-8"><title>תוכן עניינים - נספחים</title></head>
<body>
  <h1>תוכן עניינים - נספחים</h1>
  <table class="{tclass}">
    <thead>{thead}</thead>
    <tbody>
{rows_str}
    </tbody>
  </table>
</body>
</html>"""


def create_toc_pdf(toc_list: List[Dict[str, Any]],
                   output_path: str,
                   style: str = 'hebrew',
                   format_mode: str = 'auto') -> str:
    """
    Render the appendix TOC to PDF.

    Args:
        toc_list: List of dicts with at least 'id', 'name', 'page' keys.
                  May also include explicit 'label' (e.g. "נספח א'").
        output_path: Where to save the resulting PDF.
        style: 'hebrew' or 'arabic' (kept for API compatibility).
        format_mode: 'auto' | 'simple' | 'full'.

    Returns:
        The output_path.
    """
    if not HAS_WEASYPRINT:
        raise RuntimeError(
            "WeasyPrint is required for create_toc_pdf. "
            "Install via: pip install weasyprint --break-system-packages"
        )

    html_str = _build_toc_html(toc_list, style=style, format_mode=format_mode)
    HTML(string=html_str).write_pdf(output_path,
                                    stylesheets=[CSS(string=_BASE_CSS)])
    return output_path


if __name__ == '__main__':
    sample = [
        {'id': '1', 'name': 'תעודת תואר ראשון', 'page': 8},
        {'id': '2', 'name': 'תעודת הכשרה במסלול ספרנות-מידענות', 'page': 10},
        {'id': '3', 'name': 'המלצת פרופ\' ליפשיץ', 'page': 12},
    ]
    out = '/tmp/sample_toc.pdf'
    create_toc_pdf(sample, out, style='arabic')
    print(f"Sample TOC: {out}")
