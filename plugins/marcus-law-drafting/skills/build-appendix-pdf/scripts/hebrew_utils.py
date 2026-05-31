#!/usr/bin/env python3
"""Hebrew utilities for appendix numbering, formatting, font detection, and RTL rendering."""

import os
import re

HEBREW_LETTERS = [
    "א'", "ב'", "ג'", "ד'", "ה'", "ו'", "ז'", "ח'", "ט'", "י'",
    "יא'", "יב'", "יג'", "יד'", "טו'", "טז'", "יז'", "יח'", "יט'", "כ'",
    "כא'", "כב'", "כג'", "כד'", "כה'", "כו'", "כז'", "כח'", "כט'", "ל'"
]


def detect_numbering_style(text: str) -> str:
    """
    Detect if text uses Hebrew letter or Arabic numeral appendix numbering.
    
    Scans text for patterns:
    - Hebrew: "נספח א'" style references
    - Arabic: "נספח 1" style references
    
    Args:
        text: Text to analyze
    
    Returns:
        'hebrew' if Hebrew letters detected more, 'arabic' if Arabic numerals,
        defaults to 'hebrew' if ambiguous
    """
    hebrew_count = len(re.findall(r'נספח\s+[א-ת]{1,2}[\']', text))
    arabic_count = len(re.findall(r'נספח\s+\d+', text))
    
    if arabic_count > hebrew_count:
        return 'arabic'
    return 'hebrew'


def format_appendix_label(index: int, style: str) -> str:
    """
    Format full appendix label like 'נספח א\'' or 'נספח 1'.
    
    Args:
        index: 0-based appendix index
        style: 'hebrew' or 'arabic'
    
    Returns:
        Full formatted label (e.g., "נספח א'" or "נספח 1")
    
    Raises:
        ValueError: If index out of range for Hebrew style
    """
    if style == 'arabic':
        return f"נספח {index + 1}"
    
    if index < 0 or index >= len(HEBREW_LETTERS):
        raise ValueError(f"Hebrew appendix index {index} out of range (0-{len(HEBREW_LETTERS)-1})")
    
    return f"נספח {HEBREW_LETTERS[index]}"


def get_appendix_id(index: int, style: str) -> str:
    """
    Get appendix identifier like 'א\'' or '1'.
    
    Args:
        index: 0-based appendix index
        style: 'hebrew' or 'arabic'
    
    Returns:
        Just the identifier without "נספח" prefix
    
    Raises:
        ValueError: If index out of range for Hebrew style
    """
    if style == 'arabic':
        return str(index + 1)
    
    if index < 0 or index >= len(HEBREW_LETTERS):
        raise ValueError(f"Hebrew appendix index {index} out of range (0-{len(HEBREW_LETTERS)-1})")
    
    return HEBREW_LETTERS[index]


def hebrew_letter_to_index(letter: str) -> int:
    """
    Convert Hebrew letter appendix ID to 0-based index.
    
    Args:
        letter: Hebrew letter identifier (e.g., "א'" or "א")
    
    Returns:
        0-based index (0 for א, 1 for ב, etc.), or -1 if not found
    """
    letter = letter.strip()
    if not letter.endswith("'"):
        letter = letter + "'"
    
    try:
        return HEBREW_LETTERS.index(letter)
    except ValueError:
        return -1


def id_to_index(appendix_id: str, style: str) -> int:
    """
    Convert appendix ID (any style) to 0-based index.
    
    Args:
        appendix_id: Identifier to convert (e.g., "א'" or "1")
        style: 'hebrew' or 'arabic'
    
    Returns:
        0-based index, or -1 if conversion fails
    """
    if style == 'arabic':
        try:
            return int(appendix_id) - 1
        except ValueError:
            return -1
    
    return hebrew_letter_to_index(appendix_id)


def index_to_id(index: int, style: str) -> str:
    """
    Convert 0-based index to appendix ID.
    
    Args:
        index: 0-based appendix index
        style: 'hebrew' or 'arabic'
    
    Returns:
        Appendix ID without "נספח" prefix (e.g., "א'" or "1")
    
    Raises:
        ValueError: If index out of range for Hebrew style
    """
    return get_appendix_id(index, style)


def max_appendix_index(style: str) -> int:
    """
    Get maximum allowed appendix index for a given style.
    
    Args:
        style: 'hebrew' or 'arabic'
    
    Returns:
        Maximum 0-based index (29 for Hebrew, unlimited for Arabic)
    """
    if style == 'hebrew':
        return len(HEBREW_LETTERS) - 1
    return float('inf')  # type: ignore


# ─── Shared font detection and RTL rendering ───

# Try to import bidirectional text support
try:
    from bidi.algorithm import get_display
    HAS_BIDI = True
except ImportError:
    HAS_BIDI = False


def find_hebrew_font():
    """
    Find available Hebrew-capable font on system.

    Tries common font paths on Linux, Windows, and macOS.
    Prioritizes fonts with good Hebrew glyph coverage.

    Returns:
        Path to font file, or None if not found
    """
    candidates = [
        # Linux paths (prefer fonts with Hebrew support)
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/freefont/FreeSerif.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf',
        '/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf',
        '/usr/share/fonts/truetype/noto/NotoSansHebrew-Regular.ttf',
        '/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf',

        # Windows paths (prefer Hebrew-specific fonts)
        'C:\\Windows\\Fonts\\davidbl.ttf',
        'C:\\Windows\\Fonts\\frankruehl.ttf',
        'C:\\Windows\\Fonts\\arial.ttf',
        'C:\\Windows\\Fonts\\times.ttf',

        # macOS paths
        '/Library/Fonts/Arial.ttf',
        '/System/Library/Fonts/Helvetica.ttc',
    ]

    for font_path in candidates:
        if os.path.exists(font_path):
            return font_path

    return None


def bidi_text(text: str) -> str:
    """
    Apply bidirectional text rendering for Hebrew RTL text.

    IMPORTANT: Only applies bidi reordering (get_display), NOT Arabic reshaping.
    Hebrew does not need Arabic glyph reshaping — applying it corrupts Hebrew glyphs
    into tofu/boxes.

    Args:
        text: Hebrew text to render

    Returns:
        Bidirectionally formatted text, or original if bidi not available
    """
    if not HAS_BIDI:
        return text

    try:
        return get_display(text)
    except Exception:
        return text


def register_hebrew_font(canvas_obj=None):
    """
    Find and register a Hebrew-capable font for reportlab.

    Args:
        canvas_obj: Optional reportlab canvas to set font on

    Returns:
        Tuple of (font_name: str, font_path: str or None)
    """
    font_path = find_hebrew_font()

    if font_path:
        try:
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont

            font_name = 'HebrewFont'
            # Only register if not already registered
            try:
                pdfmetrics.getFont(font_name)
            except KeyError:
                pdfmetrics.registerFont(TTFont(font_name, font_path))

            return font_name, font_path
        except Exception:
            return 'Helvetica', None

    return 'Helvetica', None


if __name__ == '__main__':
    # Basic self-test
    print("Hebrew utils test:")
    
    # Test Hebrew conversions
    print(f"Hebrew letter for index 0: {get_appendix_id(0, 'hebrew')}")
    print(f"Hebrew label for index 0: {format_appendix_label(0, 'hebrew')}")
    alef = "א'"
    print(f"Index for א': {hebrew_letter_to_index(alef)}")
    print(f"ID to index א': {id_to_index(alef, 'hebrew')}")
    
    # Test Arabic conversions
    print(f"Arabic ID for index 0: {get_appendix_id(0, 'arabic')}")
    print(f"Arabic label for index 0: {format_appendix_label(0, 'arabic')}")
    print(f"ID to index 1: {id_to_index('1', 'arabic')}")
    
    # Test style detection
    text_heb = "ראו נספח א' ונספח ב'"
    text_ara = "ראו נספח 1 ונספח 2"
    print(f"Style for Hebrew text: {detect_numbering_style(text_heb)}")
    print(f"Style for Arabic text: {detect_numbering_style(text_ara)}")
    
    print("All tests passed!")
