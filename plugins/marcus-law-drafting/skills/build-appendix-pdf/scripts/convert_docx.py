#!/usr/bin/env python3
"""Convert DOCX to PDF with proper Hebrew RTL support.

Iron Rule: DOCX files MUST be converted to PDF before binding.
Uses dual pipeline strategy:
  1. Primary:   Pandoc → HTML → WeasyPrint (best Hebrew RTL rendering)
  2. Fallback:  LibreOffice headless (acceptable for non-Hebrew or simple docs)

NEVER bind a DOCX directly — it will produce broken output.

Requires: pandoc, weasyprint (pip), libreoffice (fallback)
"""

import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Tuple


def is_docx(file_path: str) -> bool:
    """
    Check if a file is a REAL DOCX document.

    Checks magic bytes first (PK ZIP header + word/ directory inside),
    then falls back to extension check only if magic bytes confirm.
    
    IMPORTANT: Some upload pipelines (e.g., Claude.ai) store DOCX content
    as UTF-8 text with a .docx extension. These are NOT real DOCX files
    and cannot be processed by Pandoc or LibreOffice DOCX parsers.

    Args:
        file_path: Path to file

    Returns:
        True only if the file is a genuine DOCX document (valid ZIP with word/ directory)
    """
    path = Path(file_path)

    # Step 1: Check magic bytes — DOCX must be a ZIP file with word/ directory
    try:
        with open(file_path, 'rb') as f:
            magic = f.read(4)
            if magic == b'PK\x03\x04':
                # Valid ZIP header — check for word/ directory (confirms DOCX)
                import zipfile
                try:
                    with zipfile.ZipFile(file_path) as zf:
                        names = zf.namelist()
                        return any(n.startswith('word/') for n in names)
                except zipfile.BadZipFile:
                    return False
    except (IOError, OSError):
        pass

    # Step 2: If file has .docx extension but is NOT a ZIP, it's NOT a real DOCX
    # This catches Claude.ai upload artifacts (UTF-8 text with .docx extension)
    return False


def check_pandoc_available() -> bool:
    """Check if Pandoc is installed."""
    try:
        result = subprocess.run(['pandoc', '--version'],
                                capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_weasyprint_available() -> bool:
    """Check if WeasyPrint is installed."""
    try:
        import weasyprint
        return True
    except ImportError:
        # Try pip install
        try:
            result = subprocess.run(
                ['pip', 'install', 'weasyprint', '--break-system-packages', '-q'],
                capture_output=True, timeout=120
            )
            if result.returncode == 0:
                import importlib
                import weasyprint
                return True
        except Exception:
            pass
    return False


def check_libreoffice_available() -> bool:
    """Check if LibreOffice is installed."""
    try:
        result = subprocess.run(['libreoffice', '--version'],
                                capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def convert_docx_pandoc_weasyprint(docx_path: str, pdf_path: str) -> Tuple[bool, str]:
    """
    Convert DOCX to PDF via Pandoc → HTML → WeasyPrint.

    This is the PRIMARY pipeline — produces the best results for Hebrew RTL
    documents, especially those created by the edit-legal-docx skill.

    Pipeline:
    1. Pandoc converts DOCX to standalone HTML with embedded styles
    2. WeasyPrint renders HTML to PDF with proper RTL, font, and table support

    Args:
        docx_path: Path to input DOCX
        pdf_path: Path for output PDF

    Returns:
        Tuple of (success: bool, message: str)
    """
    temp_dir = tempfile.mkdtemp()

    try:
        html_path = os.path.join(temp_dir, 'document.html')

        # Copy DOCX to temp dir (some sources are read-only)
        temp_docx = os.path.join(temp_dir, Path(docx_path).name)
        shutil.copy(docx_path, temp_docx)

        # Step 1: Pandoc DOCX → HTML
        # Use --embed-resources (Pandoc 3.x) with fallback to --self-contained (Pandoc 2.x)
        pandoc_args = ['pandoc', temp_docx, '-o', html_path,
                       '--standalone', '--embed-resources',
                       '--metadata', 'dir=rtl']
        pandoc_result = subprocess.run(
            pandoc_args, capture_output=True, text=True, timeout=60
        )

        # Fallback for older Pandoc versions
        if pandoc_result.returncode != 0 and '--embed-resources' in str(pandoc_result.stderr):
            pandoc_args = ['pandoc', temp_docx, '-o', html_path,
                           '--standalone', '--self-contained',
                           '--metadata', 'dir=rtl']
            pandoc_result = subprocess.run(
                pandoc_args, capture_output=True, text=True, timeout=60
            )

        if pandoc_result.returncode != 0:
            return False, f"Pandoc failed: {pandoc_result.stderr}"

        if not os.path.exists(html_path):
            return False, "Pandoc produced no output"

        # Step 2: Inject RTL CSS if not present
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        rtl_css = """
<style>
  body { direction: rtl; text-align: right; font-family: 'David', 'FrankRuehl', 'DejaVu Sans', serif; }
  table { direction: rtl; width: 100%; border-collapse: collapse; }
  th, td { text-align: right; padding: 4px 8px; }
  @page { size: A4; margin: 2.5cm; }
</style>
"""
        if 'direction: rtl' not in html_content:
            html_content = html_content.replace('</head>', rtl_css + '</head>')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

        # Step 3: WeasyPrint HTML → PDF
        try:
            from weasyprint import HTML
            HTML(filename=html_path).write_pdf(pdf_path)
        except Exception as e:
            return False, f"WeasyPrint failed: {e}"

        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
            return True, "Success (Pandoc → WeasyPrint)"
        else:
            return False, "WeasyPrint produced empty output"

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def convert_docx_libreoffice(docx_path: str, pdf_path: str) -> Tuple[bool, str]:
    """
    Convert DOCX to PDF via LibreOffice headless.

    This is the FALLBACK pipeline — produces acceptable results for simple
    documents but may break Hebrew RTL tables, headers, and complex formatting.

    Args:
        docx_path: Path to input DOCX
        pdf_path: Path for output PDF

    Returns:
        Tuple of (success: bool, message: str)
    """
    temp_dir = tempfile.mkdtemp()

    try:
        # Copy DOCX to temp dir (LibreOffice writes output in same dir)
        temp_docx = os.path.join(temp_dir, Path(docx_path).name)
        shutil.copy(docx_path, temp_docx)

        result = subprocess.run(
            ['libreoffice', '--headless', '--convert-to', 'pdf', temp_docx],
            capture_output=True, text=True, timeout=120,
            cwd=temp_dir
        )

        if result.returncode != 0:
            return False, f"LibreOffice failed: {result.stderr}"

        # Find the output PDF
        temp_pdf = os.path.join(temp_dir, Path(docx_path).stem + '.pdf')
        if os.path.exists(temp_pdf) and os.path.getsize(temp_pdf) > 0:
            shutil.copy(temp_pdf, pdf_path)
            return True, "Success (LibreOffice fallback — may have RTL issues)"
        else:
            return False, "LibreOffice produced no output"

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def convert_docx_to_pdf(docx_path: str, pdf_path: Optional[str] = None) -> Tuple[str, str]:
    """
    Convert DOCX to PDF using the best available pipeline.

    Strategy:
    1. Try Pandoc → WeasyPrint (best for Hebrew RTL)
    2. Fall back to LibreOffice headless (acceptable for simple docs)
    3. Fail with clear error if neither works

    Args:
        docx_path: Path to input DOCX
        pdf_path: Path for output PDF (None = same name with .pdf extension)

    Returns:
        Tuple of (pdf_path, method_used)

    Raises:
        RuntimeError: If no conversion pipeline is available
    """
    if pdf_path is None:
        pdf_path = str(Path(docx_path).with_suffix('.pdf'))

    print(f"  Converting DOCX → PDF: {Path(docx_path).name}")

    # Pipeline 1: Pandoc + WeasyPrint (primary)
    if check_pandoc_available():
        if check_weasyprint_available():
            success, msg = convert_docx_pandoc_weasyprint(docx_path, pdf_path)
            if success:
                print(f"    ✅ {msg}")
                return pdf_path, 'pandoc_weasyprint'
            else:
                print(f"    ⚠️ Primary pipeline failed: {msg}")
        else:
            print("    ⚠️ WeasyPrint not available")
    else:
        print("    ⚠️ Pandoc not available")

    # Pipeline 2: LibreOffice (fallback)
    if check_libreoffice_available():
        success, msg = convert_docx_libreoffice(docx_path, pdf_path)
        if success:
            print(f"    ⚠️ {msg}")
            return pdf_path, 'libreoffice'
        else:
            print(f"    ❌ Fallback also failed: {msg}")

    raise RuntimeError(
        f"Cannot convert DOCX to PDF: no working pipeline found. "
        f"Install pandoc + weasyprint (preferred) or libreoffice (fallback)."
    )


def ensure_pdf(file_path: str, output_dir: Optional[str] = None) -> Tuple[str, str]:
    """
    Ensure a file is PDF — convert if DOCX, pass through if already PDF.

    This is the main entry point called by bind_pdf.py pre-processing.

    Args:
        file_path: Path to input file (PDF or DOCX)
        output_dir: Directory for converted files (None = same directory)

    Returns:
        Tuple of (pdf_path, status):
        - pdf_path: Path to the PDF file
        - status: 'already_pdf', 'converted_pandoc_weasyprint', 
                  'converted_libreoffice', or error message
    """
    if is_docx(file_path):
        if output_dir:
            pdf_path = os.path.join(output_dir, Path(file_path).stem + '.pdf')
        else:
            pdf_path = str(Path(file_path).with_suffix('.pdf'))

        try:
            result_path, method = convert_docx_to_pdf(file_path, pdf_path)
            return result_path, f'converted_{method}'
        except RuntimeError as e:
            return file_path, f'error: {e}'
    else:
        return file_path, 'already_pdf'


if __name__ == '__main__':
    print("convert_docx.py — DOCX to PDF conversion with Hebrew RTL support")
    print(f"Pandoc available:      {check_pandoc_available()}")
    print(f"WeasyPrint available:  {check_weasyprint_available()}")
    print(f"LibreOffice available: {check_libreoffice_available()}")
