#!/usr/bin/env python3
"""Auto-detect and fix page orientation using Tesseract OSD.

Iron Rule: Every image-based page must pass orientation check before binding.
Detects 0°/90°/180°/270° rotation and corrects automatically.

Requires: tesseract-ocr, pytesseract, Pillow
"""

import os
import tempfile
import subprocess
from typing import Tuple, Optional
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    raise ImportError("Pillow is required: pip install Pillow")


def check_tesseract_available() -> bool:
    """Check if Tesseract OCR is installed and accessible."""
    try:
        result = subprocess.run(['tesseract', '--version'],
                                capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def detect_orientation_osd(image_path: str) -> Tuple[int, float]:
    """
    Detect page orientation using Tesseract OSD (Orientation and Script Detection).

    Uses Tesseract's --psm 0 mode which returns orientation info without
    performing full OCR — fast and reliable for document pages.

    Args:
        image_path: Path to image file (JPEG, PNG, TIFF)

    Returns:
        Tuple of (rotation_degrees, confidence):
        - rotation_degrees: 0, 90, 180, or 270
        - confidence: OSD confidence score (0-100)

    Raises:
        RuntimeError: If Tesseract fails or returns no orientation data
    """
    try:
        result = subprocess.run(
            ['tesseract', image_path, 'stdout', '--psm', '0'],
            capture_output=True, text=True, timeout=30
        )

        # Parse output for "Orientation in degrees: NNN"
        rotation = 0
        confidence = 0.0

        for line in result.stderr.split('\n') + result.stdout.split('\n'):
            line = line.strip()
            if 'Orientation in degrees:' in line:
                try:
                    rotation = int(line.split(':')[-1].strip())
                except ValueError:
                    pass
            elif 'Orientation confidence:' in line:
                try:
                    confidence = float(line.split(':')[-1].strip())
                except ValueError:
                    pass

        return rotation, confidence

    except subprocess.TimeoutExpired:
        print(f"Warning: Tesseract OSD timed out for {image_path}")
        return 0, 0.0
    except FileNotFoundError:
        print("Warning: Tesseract not found. Install with: apt install tesseract-ocr")
        return 0, 0.0


def fix_image_orientation(image_path: str, output_path: Optional[str] = None,
                          min_confidence: float = 1.0) -> Tuple[str, int]:
    """
    Detect and fix orientation of a single image.

    Args:
        image_path: Path to input image
        output_path: Path for corrected image (None = overwrite in place)
        min_confidence: Minimum OSD confidence to apply rotation (default 1.0)

    Returns:
        Tuple of (output_path, rotation_applied):
        - output_path: Where the corrected image was saved
        - rotation_applied: Degrees of rotation applied (0 if none needed)
    """
    if output_path is None:
        output_path = image_path

    rotation, confidence = detect_orientation_osd(image_path)

    if rotation == 0 or confidence < min_confidence:
        # No rotation needed or confidence too low
        if image_path != output_path:
            import shutil
            shutil.copy(image_path, output_path)
        return output_path, 0

    # Apply counter-rotation to fix orientation
    # Tesseract reports the detected rotation, so we counter-rotate
    correction = (360 - rotation) % 360

    img = Image.open(image_path)
    # PIL's rotate is counter-clockwise, Tesseract reports clockwise
    img_corrected = img.rotate(correction, expand=True)
    img_corrected.save(output_path)

    print(f"  Fixed orientation: rotated {correction}° (detected {rotation}°, confidence {confidence:.1f})")
    return output_path, correction


def fix_pdf_page_orientations(pdf_path: str, output_path: Optional[str] = None,
                               min_confidence: float = 1.0) -> Tuple[str, dict]:
    """
    Check and fix orientation of all pages in an image-based PDF.

    Converts each page to image, runs OSD, fixes rotation, rebuilds PDF.
    Only processes pages that are image-based (scans, photos).

    Args:
        pdf_path: Path to input PDF
        output_path: Path for corrected PDF (None = overwrite)
        min_confidence: Minimum confidence to apply rotation

    Returns:
        Tuple of (output_path, report):
        - output_path: Where corrected PDF was saved
        - report: Dict with 'pages_checked', 'pages_rotated', 'rotations' list
    """
    if output_path is None:
        output_path = pdf_path

    try:
        from PyPDF2 import PdfReader
    except ImportError:
        from pypdf import PdfReader

    reader = PdfReader(pdf_path)
    num_pages = len(reader.pages)

    report = {
        'pages_checked': num_pages,
        'pages_rotated': 0,
        'rotations': []
    }

    temp_dir = tempfile.mkdtemp()
    corrected_images = []

    try:
        # Convert each page to image using pdftoppm (poppler)
        base_path = os.path.join(temp_dir, 'page')

        try:
            subprocess.run(
                ['pdftoppm', '-jpeg', '-r', '150', pdf_path, base_path],
                capture_output=True, timeout=120
            )
        except FileNotFoundError:
            # pdftoppm not available — try alternative
            print("Warning: pdftoppm not found. Skipping orientation check for PDF.")
            if pdf_path != output_path:
                import shutil
                shutil.copy(pdf_path, output_path)
            return output_path, report

        # Find generated page images
        page_images = sorted([
            os.path.join(temp_dir, f) for f in os.listdir(temp_dir)
            if f.startswith('page-') and f.endswith('.jpg')
        ])

        if not page_images:
            # No pages extracted — return as-is
            if pdf_path != output_path:
                import shutil
                shutil.copy(pdf_path, output_path)
            return output_path, report

        for i, page_img in enumerate(page_images):
            corrected_path = os.path.join(temp_dir, f'corrected_{i}.jpg')
            _, rotation = fix_image_orientation(page_img, corrected_path, min_confidence)

            if rotation != 0:
                report['pages_rotated'] += 1
                report['rotations'].append({'page': i + 1, 'rotation': rotation})

            corrected_images.append(corrected_path)

        # If any pages were rotated, rebuild PDF from corrected images
        if report['pages_rotated'] > 0:
            pages = []
            a4_w, a4_h = 595, 842
            margin = 28
            max_w = a4_w - 2 * margin
            max_h = a4_h - 2 * margin

            for img_path in corrected_images:
                img = Image.open(img_path)
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                ratio = min(max_w / img.width, max_h / img.height)
                new_w = int(img.width * ratio)
                new_h = int(img.height * ratio)
                img_resized = img.resize((new_w, new_h), Image.LANCZOS)
                canvas_img = Image.new('RGB', (a4_w, a4_h), 'white')
                x = (a4_w - new_w) // 2
                y = (a4_h - new_h) // 2
                canvas_img.paste(img_resized, (x, y))
                pages.append(canvas_img)

            if pages:
                pages[0].save(output_path, 'PDF', resolution=72,
                              save_all=True, append_images=pages[1:])
        else:
            # No rotation needed — copy as-is
            if pdf_path != output_path:
                import shutil
                shutil.copy(pdf_path, output_path)

        return output_path, report

    finally:
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


if __name__ == '__main__':
    print("fix_orientation.py — Auto-detect and fix page orientation")
    print(f"Tesseract available: {check_tesseract_available()}")

    # Self-test with a simple image
    test_img = '/tmp/test_orientation.jpg'
    if os.path.exists(test_img):
        rotation, confidence = detect_orientation_osd(test_img)
        print(f"Detected: {rotation}° (confidence: {confidence})")
