#!/usr/bin/env python3
"""Compress PDF for court filing upload (net hamishpat).

Net hamishpat limit: 30MB per file. Files over 30MB must be split.
This script compresses PDFs using Ghostscript to reduce file size
while preserving readability for court submission.

Three quality levels:
  /printer  — high quality, minimal compression (best for text-heavy docs)
  /ebook    — balanced (default, good for mixed text+images)
  /screen   — maximum compression (for very heavy scan-based files)
"""

import os
import subprocess
import shutil
from typing import Tuple, Optional

NET_HAMISHPAT_LIMIT_MB = 30


def check_ghostscript_available() -> bool:
    """Check if Ghostscript is installed."""
    try:
        result = subprocess.run(['gs', '--version'],
                                capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def install_ghostscript() -> bool:
    """Try to install Ghostscript via apt."""
    try:
        result = subprocess.run(
            ['apt-get', 'install', '-y', '-qq', 'ghostscript'],
            capture_output=True, timeout=120
        )
        return result.returncode == 0
    except Exception:
        return False


def compress_pdf(input_path: str,
                 output_path: Optional[str] = None,
                 quality: str = 'ebook') -> dict:
    """
    Compress a PDF file using Ghostscript.

    Args:
        input_path: Path to input PDF
        output_path: Path for compressed PDF (None = overwrite)
        quality: 'printer' (high), 'ebook' (balanced), 'screen' (max compression)

    Returns:
        Dict with compression results:
        - input_path, output_path
        - input_size_mb, output_size_mb
        - reduction_percent
        - quality_used
        - pages_preserved (bool)
    """
    if output_path is None:
        output_path = input_path

    if quality not in ('printer', 'ebook', 'screen'):
        quality = 'ebook'

    # Ensure Ghostscript is available
    if not check_ghostscript_available():
        print("  Installing Ghostscript...")
        if not install_ghostscript():
            return {
                'error': 'Ghostscript not available and cannot be installed',
                'input_path': input_path,
                'output_path': output_path,
            }

    input_size = os.path.getsize(input_path)

    # Count pages before
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        from pypdf import PdfReader
    
    reader = PdfReader(input_path)
    input_pages = len(reader.pages)

    # Compress via Ghostscript
    import tempfile
    temp_output = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    temp_output.close()

    try:
        result = subprocess.run([
            'gs', '-sDEVICE=pdfwrite',
            '-dCompatibilityLevel=1.4',
            f'-dPDFSETTINGS=/{quality}',
            '-dNOPAUSE', '-dBATCH', '-dQUIET',
            f'-sOutputFile={temp_output.name}',
            input_path
        ], capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            os.unlink(temp_output.name)
            return {
                'error': f'Ghostscript failed: {result.stderr}',
                'input_path': input_path,
                'output_path': output_path,
            }

        output_size = os.path.getsize(temp_output.name)

        # Verify pages preserved
        reader2 = PdfReader(temp_output.name)
        output_pages = len(reader2.pages)

        # Only use compressed version if it's actually smaller
        if output_size < input_size:
            shutil.copy(temp_output.name, output_path)
        else:
            if input_path != output_path:
                shutil.copy(input_path, output_path)
            output_size = input_size

        os.unlink(temp_output.name)

        reduction = (1 - output_size / input_size) * 100 if input_size > 0 else 0

        return {
            'input_path': input_path,
            'output_path': output_path,
            'input_size_mb': round(input_size / 1024 / 1024, 2),
            'output_size_mb': round(output_size / 1024 / 1024, 2),
            'reduction_percent': round(reduction, 1),
            'quality_used': quality,
            'input_pages': input_pages,
            'output_pages': output_pages,
            'pages_preserved': input_pages == output_pages,
            'under_net_hamishpat_limit': output_size / 1024 / 1024 < NET_HAMISHPAT_LIMIT_MB,
        }

    except subprocess.TimeoutExpired:
        if os.path.exists(temp_output.name):
            os.unlink(temp_output.name)
        return {
            'error': 'Ghostscript timed out (file too large?)',
            'input_path': input_path,
            'output_path': output_path,
        }


def auto_compress_for_court(input_path: str,
                            output_path: Optional[str] = None) -> dict:
    """
    Smart compression for court filing.

    Strategy:
    1. If file < 5MB: skip (already small enough)
    2. If file 5-30MB: compress with /ebook
    3. If file > 30MB: compress with /screen, warn if still over limit
    4. Report net hamishpat compliance

    Args:
        input_path: Path to input PDF
        output_path: Path for output (None = same name + _compressed)

    Returns:
        Compression result dict
    """
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_compressed{ext}"

    size_mb = os.path.getsize(input_path) / 1024 / 1024

    if size_mb < 5:
        print(f"  ✅ File is {size_mb:.1f}MB — no compression needed")
        if input_path != output_path:
            shutil.copy(input_path, output_path)
        return {
            'input_path': input_path,
            'output_path': output_path,
            'input_size_mb': round(size_mb, 2),
            'output_size_mb': round(size_mb, 2),
            'reduction_percent': 0,
            'quality_used': 'none',
            'skipped': True,
            'under_net_hamishpat_limit': size_mb < NET_HAMISHPAT_LIMIT_MB,
        }

    if size_mb <= NET_HAMISHPAT_LIMIT_MB:
        quality = 'ebook'
        print(f"  📦 File is {size_mb:.1f}MB — compressing with /ebook")
    else:
        quality = 'screen'
        print(f"  ⚠️ File is {size_mb:.1f}MB (over 30MB limit!) — compressing with /screen")

    result = compress_pdf(input_path, output_path, quality)

    if 'error' not in result:
        if result['under_net_hamishpat_limit']:
            print(f"  ✅ {result['input_size_mb']}MB → {result['output_size_mb']}MB ({result['reduction_percent']}% reduction)")
        else:
            print(f"  ⚠️ {result['output_size_mb']}MB — still over 30MB limit. Consider splitting into volumes.")

    return result


if __name__ == '__main__':
    print("compress_pdf.py — PDF compression for court filing")
    print(f"Ghostscript available: {check_ghostscript_available()}")
    print(f"Net hamishpat limit: {NET_HAMISHPAT_LIMIT_MB}MB")
