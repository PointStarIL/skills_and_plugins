#!/usr/bin/env python3
"""
Install Microsoft Word fonts (David, Times New Roman, Arial) into the
user's font cache so LibreOffice and WeasyPrint can render Hebrew legal
documents the way Word does.

Why this matters:
The Linux sandbox does not ship with David, Times New Roman, or Arial.
Without them, LibreOffice headless silently substitutes DejaVu Sans for
all body text - destroying the document's visual identity. Once the real
fonts are present, LibreOffice produces a near-identical match to the
user's manual Word export.

Bundled TTFs live in <skill>/fonts/. The first call to
ensure_fonts_installed() on a new machine copies them to ~/.fonts and
refreshes fc-cache automatically.

Public API:
    ensure_fonts_installed()           -> bool   no-op if already installed
    install_from_directory(font_dir)   -> int    copy + refresh
    list_available_families()          -> set
    already_installed()                -> bool
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

REQUIRED_FAMILIES = ['David', 'Times New Roman', 'Arial']

# The skill ships fonts in <skill_root>/fonts/
_SKILL_FONTS_DIR = Path(__file__).resolve().parent.parent / 'fonts'


def list_available_families():
    """Return the set of font family names known to fontconfig."""
    try:
        out = subprocess.run(
            ['fc-list', ':lang=he,en', 'family'],
            capture_output=True, text=True, timeout=10,
        )
        names = set()
        for line in out.stdout.splitlines():
            for fam in line.split(','):
                names.add(fam.strip())
        return names
    except Exception:
        return set()


def already_installed():
    """Return True iff David, Times New Roman, and Arial are all available."""
    fams = list_available_families()
    return all(req in fams for req in REQUIRED_FAMILIES)


def install_from_directory(font_dir):
    """Copy every .ttf / .otf from font_dir into ~/.fonts and refresh cache."""
    src = Path(font_dir)
    if not src.is_dir():
        raise ValueError(f"Not a directory: {src}")
    target = Path.home() / '.fonts'
    target.mkdir(exist_ok=True)
    copied = 0
    for f in src.iterdir():
        if f.suffix.lower() in ('.ttf', '.otf'):
            shutil.copy(f, target / f.name)
            copied += 1
    if copied:
        try:
            subprocess.run(['fc-cache', '-fv', str(target)],
                           capture_output=True, timeout=30)
        except Exception as e:
            print(f"warning: fc-cache failed: {e}")
    return copied


def ensure_fonts_installed(verbose=True):
    """
    Ensure David / Times New Roman / Arial are installed.

    Strategy:
    1. If all required families are already in fontconfig, return True (no-op).
    2. Otherwise, try to install from the bundled <skill>/fonts/ folder.
    3. Return True iff all required families are available after install.
    """
    if already_installed():
        return True
    if not _SKILL_FONTS_DIR.is_dir():
        if verbose:
            print(f"warning: fonts folder not found: {_SKILL_FONTS_DIR}")
        return False
    if verbose:
        print(f"-- Auto-installing Word fonts from {_SKILL_FONTS_DIR.name}/ --")
    n = install_from_directory(_SKILL_FONTS_DIR)
    if verbose:
        print(f"   copied {n} TTF files to ~/.fonts")
    ok = already_installed()
    if verbose:
        if ok:
            print("   David, Times New Roman, Arial all available")
        else:
            avail = list_available_families()
            missing = [f for f in REQUIRED_FAMILIES if f not in avail]
            print(f"   warning: still missing {missing}")
    return ok


def main():
    if len(sys.argv) > 1:
        font_dir = sys.argv[1]
        if already_installed():
            print("All required Word fonts already installed.")
            return
        print(f"Installing fonts from {font_dir}...")
        n = install_from_directory(font_dir)
        print(f"  copied {n} TTF files to ~/.fonts")
    else:
        # Default: use the bundled fonts folder
        ensure_fonts_installed()


if __name__ == '__main__':
    main()
