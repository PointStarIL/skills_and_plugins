# Installation (v3)

## 1. System packages (Ubuntu / Debian)
```
sudo apt install pandoc tesseract-ocr tesseract-ocr-heb \
                 poppler-utils libreoffice ghostscript fontconfig
```

## 2. Python packages
```
pip install weasyprint pymupdf pypdf python-docx pillow python-bidi \
            --break-system-packages
```

## 3. Word fonts (CRUCIAL for Hebrew fidelity)

Without David, Times New Roman, and Arial installed, LibreOffice silently
falls back to DejaVu Sans - and your Hebrew legal pleading suddenly looks
like a Linux command-line manual.

Get the TTF files from a Windows machine:
- C:\Windows\Fonts\david.ttf and davidbd.ttf
- C:\Windows\Fonts\times.ttf, timesbd.ttf, timesi.ttf, timesbi.ttf
- C:\Windows\Fonts\arial.ttf, arialbd.ttf, ariali.ttf, arialbi.ttf, ariblk.ttf

Copy them into a single folder, then run:
```
python scripts/install_fonts.py /path/to/fonts_folder
```

The script copies them to ~/.fonts and refreshes fc-cache.

## 4. Drop into your skills directory

Copy the entire legal-appendix-builder/ folder into:
- Cowork:      ~/AppData/Roaming/Claude/.../skills-plugin/.../skills/
- Claude Code: ~/.claude/skills/

## 5. Quick smoke test

```python
import sys; sys.path.insert(0, 'scripts')
from prepare_docx import prepare_pleading
from bind_pdf import bind_pleading

# 1. Pre-process the DOCX (1.5 body, 1.15 tables, dash sanitisation)
prepare_pleading('pleading.docx', '/tmp/spaced.docx')

# 2. Bind
result = bind_pleading(
    pleading_path='/tmp/spaced.docx',
    appendix_files=['nispach_1.pdf', 'nispach_2.pdf'],
    appendix_list=[
        {'id': '1', 'name': 'Description for nispach 1'},
        {'id': '2', 'name': 'Description for nispach 2'},
    ],
    output_path='out.pdf',
    style='arabic',
)
print(f"{result['total_pages']} pages, match={result['pages_match']}")
```

## 6. Verifying the em-dash ban

Run:
```
python -c "
import fitz
doc = fitz.open('out.pdf')
for page in doc:
    if chr(0x2014) in page.get_text():
        print(f'EM DASH on page {page.number+1}')
        break
else:
    print('clean')
"
```

If the output is anything other than 'clean', the em dash came from the
ORIGINAL DOCX content (not from Claude's chrome) - check the source
document or run prepare_docx.py first.
