#!/usr/bin/env python3
"""
Create Hebrew RTL cover (separator) pages for legal appendix package.

REWRITTEN: Uses WeasyPrint (HTML→PDF) instead of reportlab+bidi.
Each appendix gets a single A4 page with three centred zones:
top-pad → label → accent line → name → accent line → bottom-pad.

The previous reportlab approach physically reversed Hebrew glyphs,
which broke RTL viewers. WeasyPrint relies on HarfBuzz/Pango shaping
so RTL layout is correct without manual reversal.

Public API preserved:
    create_cover_pages_pdf(appendix_list, output_path, style='hebrew')
"""

import os
import tempfile
from typing import List, Dict, Any

try:
    from weasyprint import HTML, CSS
    HAS_WEASYPRINT = True
except ImportError:
    HAS_WEASYPRINT = False

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False


_BASE_CSS = """
@page { size: A4; margin: 3cm 2.5cm; }
html, body { margin: 0; padding: 0; direction: rtl;
             font-family: 'David', 'FrankRuehl CLM', 'DejaVu Sans', sans-serif;
             color: #1a1a1a; }
.wrap { width: 100%; text-align: center; padding-top: 8cm; }
.label { font-size: 48pt; font-weight: bold; color: #1a1a1a;
         margin: 0 0 25px 0; line-height: 1.2; }
.accent { width: 50%; height: 3px; background: #2C5F8A;
          margin: 25px auto; border: 0; }
.name { font-size: 18pt; color: #333; line-height: 1.6;
        max-width: 14cm; margin: 0 auto; }
"""


def _format_label_text(item: Dict[str, Any]) -> str:
    """Return the displayed appendix identifier such as 'א'' or '1'."""
    if 'label' in item and item['label']:
        # Strip leading 'נספח ' if present so we don't get "נספח נספח א'"
        lbl = str(item['label']).strip()
        prefix = 'נספח'
        if lbl.startswith(prefix):
            return lbl[len(prefix):].strip()
        return lbl
    return str(item.get('id', '?'))


def _build_cover_html(label: str, name: str) -> str:
    """Build single-page cover HTML."""
    return f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head><meta charset="utf-8"><title>נספח {label}</title></head>
<body>
  <div class="wrap">
    <div class="label">נספח {label}</div>
    <hr class="accent">
    <div class="name">{name}</div>
    <hr class="accent">
  </div>
</body>
</html>"""


def create_cover_pages_pdf(appendix_list: List[Dict[str, Any]],
                           output_path: str,
                           style: str = 'hebrew') -> str:
    """
    Render one cover page per appendix into a single PDF.

    Args:
        appendix_list: List of dicts with at least 'id'/'label' and 'name'.
        output_path: Where to save the multi-page PDF.
        style: 'hebrew' or 'arabic' (kept for API compatibility).

    Returns:
        The output_path.
    """
    if not HAS_WEASYPRINT:
        raise RuntimeError(
            "WeasyPrint is required for create_cover_pages_pdf. "
            "Install via: pip install weasyprint --break-system-packages"
        )

    # Render each cover individually then merge with PyMuPDF (preferred) or pypdf.
    work = tempfile.mkdtemp(prefix='covers_')
    try:
        per_page_pdfs = []
        for i, item in enumerate(appendix_list):
            lbl = _format_label_text(item)
            name = str(item.get('name', ''))
            html_str = _build_cover_html(lbl, name)
            single = os.path.join(work, f'cover_{i:03d}.pdf')
            HTML(string=html_str).write_pdf(single,
                                            stylesheets=[CSS(string=_BASE_CSS)])
            per_page_pdfs.append(single)

        # Merge all single-page covers
        if HAS_PYMUPDF:
            merged = fitz.open()
            for p in per_page_pdfs:
                src = fitz.open(p)
                merged.insert_pdf(src)
                src.close()
            merged.save(output_path, garbage=4, deflate=True)
            merged.close()
        else:
            # Fallback: pypdf
            try:
                from pypdf import PdfMerger
            except ImportError:
                from PyPDF2 import PdfMerger
            merger = PdfMerger()
            for p in per_page_pdfs:
                merger.append(p)
            merger.write(output_path)
            merger.close()

        return output_path
    finally:
        import shutil
        shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    sample = [
        {'id': '1', 'name': 'תעודת תואר ראשון - בר-אילן'},
        {'id': '2', 'name': 'תעודת הכשרה - דוד ילין'},
        {'id': '3', 'name': 'המלצה - פרופ\' ליפשיץ'},
    ]
    out = '/tmp/sample_covers.pdf'
    create_cover_pages_pdf(sample, out, style='arabic')
    print(f"Sample covers: {out}")
