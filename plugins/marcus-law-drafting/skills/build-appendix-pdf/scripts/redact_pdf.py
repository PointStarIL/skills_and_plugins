#!/usr/bin/env python3
"""Redact sensitive information from PDF before sending to opposing party.

USE CASE: Removing personal data (ID, phone, email, address, bank account)
from court filings before serving to the other side. This is NOT anonymization
for AI processing — it's legal redaction for document disclosure.

Two modes:
  Mode A — Text-based PDF: Direct search + redact (automatic, reliable)
  Mode B — Image-based PDF: OCR + search + Human Gate (requires user approval)

Human Gate: The script ALWAYS asks what to redact before executing.
Default categories: ID number, phone, email, address, bank account.
User can add custom terms.
"""

import os
import subprocess
import tempfile
from typing import List, Dict, Optional, Tuple

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


# ─── Default redaction categories ───

DEFAULT_CATEGORIES = {
    'id_number': {
        'label_he': 'מספר זהות',
        'label_en': 'ID number',
        'description': 'ת.ז. / מספר זהות',
    },
    'phone': {
        'label_he': 'טלפון',
        'label_en': 'Phone',
        'description': 'מספרי טלפון',
    },
    'email': {
        'label_he': 'אימייל',
        'label_en': 'Email',
        'description': 'כתובות דוא"ל',
    },
    'address': {
        'label_he': 'כתובת',
        'label_en': 'Address',
        'description': 'כתובת מגורים / עסק',
    },
    'bank_account': {
        'label_he': 'חשבון בנק',
        'label_en': 'Bank account',
        'description': 'מספר חשבון / סניף / בנק',
    },
}


def check_pymupdf_available() -> bool:
    """Check if PyMuPDF is installed."""
    return fitz is not None


def install_pymupdf() -> bool:
    """Try to install PyMuPDF via pip."""
    try:
        result = subprocess.run(
            ['pip', 'install', 'pymupdf', '--break-system-packages', '-q'],
            capture_output=True, timeout=120
        )
        if result.returncode == 0:
            global fitz
            import fitz as _fitz
            fitz = _fitz
            return True
    except Exception:
        pass
    return False


def classify_page(page) -> str:
    """
    Classify a PDF page as 'text' or 'image'.
    
    A page with less than 20 characters of extractable text
    is considered image-based and requires OCR.
    
    Args:
        page: PyMuPDF page object
    
    Returns:
        'text' or 'image'
    """
    text = page.get_text().strip()
    return 'text' if len(text) >= 20 else 'image'


def ocr_page_text(page, lang: str = 'heb+eng') -> str:
    """
    Extract text from an image-based page using Tesseract OCR.
    
    Args:
        page: PyMuPDF page object
        lang: Tesseract language (default: Hebrew + English)
    
    Returns:
        OCR-extracted text
    """
    # Render page to high-res image
    pix = page.get_pixmap(dpi=300)
    temp_img = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    pix.save(temp_img.name)
    
    try:
        result = subprocess.run(
            ['tesseract', temp_img.name, 'stdout', '-l', lang, '--psm', '6'],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ''
    finally:
        os.unlink(temp_img.name)


def scan_document(pdf_path: str, search_terms: List[str]) -> dict:
    """
    Scan a PDF for sensitive terms. Reports what was found and where,
    separated by text pages (reliable) and image pages (OCR, less reliable).
    
    This is the PRE-REDACTION scan — generates a report for Human Gate approval.
    
    Args:
        pdf_path: Path to PDF file
        search_terms: List of strings to search for
    
    Returns:
        Dict with scan results:
        - total_pages: int
        - text_pages: list of page numbers (0-based) that are text
        - image_pages: list of page numbers that are image
        - findings: list of {term, page, page_type, confidence}
        - not_found: list of terms not found anywhere
    """
    if not check_pymupdf_available():
        install_pymupdf()
    
    doc = fitz.open(pdf_path)
    
    result = {
        'total_pages': len(doc),
        'text_pages': [],
        'image_pages': [],
        'findings': [],
        'not_found': [],
    }
    
    found_terms = set()
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_type = classify_page(page)
        
        if page_type == 'text':
            result['text_pages'].append(page_num + 1)
            text = page.get_text()
        else:
            result['image_pages'].append(page_num + 1)
            text = ocr_page_text(page)
        
        for term in search_terms:
            if term in text:
                confidence = 'high' if page_type == 'text' else 'medium'
                result['findings'].append({
                    'term': term,
                    'page': page_num + 1,
                    'page_type': page_type,
                    'confidence': confidence,
                })
                found_terms.add(term)
    
    result['not_found'] = [t for t in search_terms if t not in found_terms]
    doc.close()
    
    return result


def format_scan_report(scan_result: dict) -> str:
    """
    Format scan results as a readable Hebrew report for Human Gate.
    
    Args:
        scan_result: Output from scan_document()
    
    Returns:
        Formatted report string
    """
    lines = []
    lines.append("── דו\"ח סריקה להשחרה ──")
    lines.append(f"  סה\"כ עמודים: {scan_result['total_pages']}")
    lines.append(f"  עמודים טקסטואליים: {len(scan_result['text_pages'])}")
    lines.append(f"  עמודים מבוססי תמונה: {len(scan_result['image_pages'])}")
    lines.append("")
    
    if scan_result['findings']:
        lines.append("  נמצא:")
        for f in scan_result['findings']:
            confidence_icon = "✅" if f['confidence'] == 'high' else "⚠️"
            lines.append(f"    {confidence_icon} \"{f['term']}\" — עמ' {f['page']} ({f['page_type']}, {f['confidence']})")
    else:
        lines.append("  ❌ לא נמצאו ביטויים")
    
    if scan_result['not_found']:
        lines.append("")
        lines.append("  לא נמצא:")
        for term in scan_result['not_found']:
            lines.append(f"    ❓ \"{term}\" — לא נמצא בשום עמוד")
        if scan_result['image_pages']:
            lines.append(f"    💡 ייתכן שמופיע בעמודי תמונה ({len(scan_result['image_pages'])} עמ') — OCR לא תמיד מזהה עברית במדויק")
    
    return '\n'.join(lines)


def redact_document(pdf_path: str,
                    output_path: str,
                    terms: List[str],
                    redact_image_pages: bool = False) -> dict:
    """
    Execute redaction on a PDF. Removes text permanently — not reversible.
    
    IMPORTANT: This should only be called AFTER Human Gate approval.
    
    Args:
        pdf_path: Path to input PDF
        output_path: Path for redacted output
        terms: List of terms to redact
        redact_image_pages: If True, attempt OCR-based redaction on image pages
    
    Returns:
        Dict with redaction results:
        - redactions_applied: total count
        - per_page: list of {page, count, terms_found}
        - verified_removed: list of terms confirmed removed
        - verification_failed: list of terms still extractable (should be empty)
    """
    if not check_pymupdf_available():
        install_pymupdf()
    
    doc = fitz.open(pdf_path)
    
    result = {
        'redactions_applied': 0,
        'per_page': [],
        'verified_removed': [],
        'verification_failed': [],
    }
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_type = classify_page(page)
        page_count = 0
        page_terms = []
        
        if page_type == 'text':
            # Mode A: Direct text search and redact
            for term in terms:
                areas = page.search_for(term)
                for area in areas:
                    page.add_redact_annot(area, fill=(0, 0, 0))
                    page_count += 1
                if areas:
                    page_terms.append(term)
            
            if page_count > 0:
                page.apply_redactions()
        
        elif page_type == 'image' and redact_image_pages:
            # Mode B: OCR-assisted redaction
            # Render to image, OCR for coordinates, redact
            pix = page.get_pixmap(dpi=300)
            temp_img = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            pix.save(temp_img.name)
            
            try:
                tsv_result = subprocess.run(
                    ['tesseract', temp_img.name, 'stdout', '-l', 'heb+eng', '--psm', '6', 'tsv'],
                    capture_output=True, text=True, timeout=30
                )
                
                # Parse TSV for word coordinates
                words_data = []
                lines = tsv_result.stdout.strip().split('\n')
                for line in lines[1:]:
                    parts = line.split('\t')
                    if len(parts) >= 12 and parts[11].strip():
                        try:
                            words_data.append({
                                'text': parts[11].strip(),
                                'left': int(parts[6]),
                                'top': int(parts[7]),
                                'width': int(parts[8]),
                                'height': int(parts[9]),
                            })
                        except ValueError:
                            pass
                
                # Search terms in OCR words
                scale = 72.0 / 300.0
                for term in terms:
                    for wd in words_data:
                        if term in wd['text']:
                            x0 = wd['left'] * scale
                            y0 = wd['top'] * scale
                            x1 = (wd['left'] + wd['width']) * scale
                            y1 = (wd['top'] + wd['height']) * scale
                            page.add_redact_annot(fitz.Rect(x0, y0, x1, y1), fill=(0, 0, 0))
                            page_count += 1
                            if term not in page_terms:
                                page_terms.append(term)
                
                if page_count > 0:
                    page.apply_redactions()
                    
            except Exception as e:
                print(f"  ⚠️ OCR redaction failed on page {page_num + 1}: {e}")
            finally:
                os.unlink(temp_img.name)
        
        if page_count > 0:
            result['per_page'].append({
                'page': page_num + 1,
                'count': page_count,
                'terms_found': page_terms,
                'page_type': page_type,
            })
            result['redactions_applied'] += page_count
    
    # Save redacted document
    doc.save(output_path)
    doc.close()
    
    # ── Verification pass ──
    # Re-open and verify that redacted terms are no longer extractable
    doc_verify = fitz.open(output_path)
    all_text = ''
    for page in doc_verify:
        all_text += page.get_text()
    doc_verify.close()
    
    for term in terms:
        if term in all_text:
            result['verification_failed'].append(term)
        else:
            result['verified_removed'].append(term)
    
    return result


def format_redaction_report(redact_result: dict) -> str:
    """
    Format redaction results as a readable report.
    
    Args:
        redact_result: Output from redact_document()
    
    Returns:
        Formatted report string
    """
    lines = []
    lines.append("── דו\"ח השחרה ──")
    lines.append(f"  סה\"כ השחרות: {redact_result['redactions_applied']}")
    
    if redact_result['per_page']:
        lines.append("")
        for entry in redact_result['per_page']:
            terms_str = ', '.join(entry['terms_found'])
            lines.append(f"  עמ' {entry['page']}: {entry['count']} השחרות ({entry['page_type']}) — {terms_str}")
    
    lines.append("")
    lines.append("  אימות:")
    for term in redact_result['verified_removed']:
        lines.append(f"    ✅ \"{term}\" — נמחק לחלוטין")
    for term in redact_result['verification_failed']:
        lines.append(f"    ❌ \"{term}\" — עדיין ניתן לחילוץ! בדיקה ידנית נדרשת")
    
    return '\n'.join(lines)


def build_human_gate_prompt(scan_result: dict, categories_used: dict) -> str:
    """
    Build the Human Gate prompt — what to show the user before redacting.
    
    Args:
        scan_result: Output from scan_document()
        categories_used: Dict of category_id → terms
    
    Returns:
        Formatted prompt for user approval
    """
    lines = []
    lines.append("🔒 השחרה לפני שליחה לצד שכנגד")
    lines.append("")
    lines.append("ביטויים לחיפוש:")
    for cat_id, terms in categories_used.items():
        cat = DEFAULT_CATEGORIES.get(cat_id, {'label_he': cat_id})
        lines.append(f"  {cat['label_he']}: {', '.join(terms)}")
    
    lines.append("")
    lines.append(format_scan_report(scan_result))
    
    if scan_result['image_pages']:
        lines.append("")
        lines.append(f"  ⚠️ {len(scan_result['image_pages'])} עמודים מבוססי תמונה — OCR עלול לפספס.")
        lines.append("  מומלץ לבדוק ידנית את העמודים: " + 
                     ', '.join(str(p) for p in scan_result['image_pages']))
    
    lines.append("")
    lines.append("לאשר השחרה? (כן / לא / להוסיף ביטויים)")
    
    return '\n'.join(lines)


if __name__ == '__main__':
    print("redact_pdf.py — Redaction before sending to opposing party")
    print(f"PyMuPDF available: {check_pymupdf_available()}")
    print(f"Default categories: {', '.join(DEFAULT_CATEGORIES.keys())}")
