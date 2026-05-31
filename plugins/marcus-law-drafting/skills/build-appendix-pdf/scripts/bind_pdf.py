#!/usr/bin/env python3
"""bind_pdf v3.1 - PyMuPDF merge, LibreOffice DOCX, em-dash sanitised, auto-install fonts."""
import os, shutil, subprocess, tempfile
from pathlib import Path
from typing import List, Dict, Any
import fitz
from hebrew_utils import format_appendix_label, get_appendix_id
from create_cover_pages import create_cover_pages_pdf
from create_toc import create_toc_pdf
from convert_docx import is_docx, ensure_pdf
from fix_orientation import check_tesseract_available, fix_pdf_page_orientations
from sanitize_text import sanitize, sanitize_appendix_list
from install_fonts import ensure_fonts_installed


def count_pdf_pages(path):
    try:
        d = fitz.open(path); n = d.page_count; d.close(); return n
    except Exception as e:
        print(f"warn: {e}"); return 0


def add_page_numbers(input_pdf, output_pdf, start_num=1):
    doc = fitz.open(input_pdf)
    for i, page in enumerate(doc):
        rect = page.rect
        text = str(start_num + i)
        tb = fitz.Rect(rect.x0, rect.y1 - 28, rect.x1, rect.y1 - 10)
        page.insert_textbox(tb, text, fontsize=10, fontname="helv",
                            align=fitz.TEXT_ALIGN_CENTER, color=(0.2, 0.2, 0.2))
    tmp = output_pdf + '.tmp'
    doc.save(tmp, garbage=4, deflate=True); doc.close()
    shutil.move(tmp, output_pdf)
    return output_pdf


def add_bookmarks_to_pdf(input_pdf, output_pdf, page_map, pleading_pages, toc_page):
    doc = fitz.open(input_pdf)
    toc = []
    toc.append([1, "כתב הטענות", 1])
    toc.append([1, "תוכן עניינים - נספחים", toc_page])
    for entry in page_map:
        label = sanitize(entry.get('label', f"נספח {entry.get('id','?')}"))
        toc.append([1, label, entry['cover_page']])
    doc.set_toc(toc)
    tmp = output_pdf + '.tmp'
    doc.save(tmp, garbage=4, deflate=True); doc.close()
    shutil.move(tmp, output_pdf)
    return output_pdf


def _convert_docx_libreoffice(docx_path, work_dir):
    src = os.path.join(work_dir, Path(docx_path).name)
    shutil.copy(docx_path, src)
    result = subprocess.run(
        ['libreoffice', '--headless', '--convert-to', 'pdf', src],
        capture_output=True, text=True, timeout=180, cwd=work_dir,
    )
    pdf = os.path.join(work_dir, Path(docx_path).stem + '.pdf')
    if not os.path.exists(pdf):
        raise RuntimeError(f"LibreOffice failed: {result.stderr}")
    return pdf


def preprocess_files(pleading_path, appendix_files, work_dir, fix_orientation=True):
    report = {'pleading_converted': False, 'pleading_method': None,
              'appendices_converted': [], 'orientation_fixes': []}
    print("\n-- Pre-processing: DOCX detection --")
    if is_docx(pleading_path):
        print("  Pleading is DOCX - converting via LibreOffice + system fonts...")
        try:
            new_path = _convert_docx_libreoffice(pleading_path, work_dir)
            status = 'converted_libreoffice'
        except Exception as e:
            print(f"  LibreOffice failed ({e}) - fallback ensure_pdf")
            new_path, status = ensure_pdf(pleading_path, output_dir=work_dir)
            if status.startswith('error'):
                raise RuntimeError(f"Pleading conversion failed: {status}")
        pleading_path = new_path
        report['pleading_converted'] = True
        report['pleading_method'] = status
    new_apps = []
    for i, f in enumerate(appendix_files):
        if is_docx(f):
            print(f"  Appendix {i+1} DOCX - converting...")
            np, st = ensure_pdf(f, output_dir=work_dir)
            if st.startswith('error'):
                raise RuntimeError(f"Appendix {i+1} failed: {st}")
            new_apps.append(np)
            report['appendices_converted'].append({'index': i, 'original': f, 'method': st})
        else:
            new_apps.append(f)
    if fix_orientation and check_tesseract_available():
        print("\n-- Pre-processing: Orientation check --")
        for i, f in enumerate(new_apps):
            try:
                fp, fr = fix_pdf_page_orientations(f, output_dir=work_dir)
                if fr.get('rotated_pages'):
                    print(f"  Rotated {len(fr['rotated_pages'])} page(s) in app {i+1}")
                    new_apps[i] = fp
                    report['orientation_fixes'].append({'index': i, 'fixes': fr['rotated_pages']})
            except Exception as e:
                print(f"  Orientation check failed for app {i+1}: {e}")
    elif fix_orientation:
        print("\n-- Tesseract unavailable - skip orientation --")
    return pleading_path, new_apps, report


def bind_pleading(pleading_path, appendix_files, appendix_list, output_path,
                  style='hebrew', toc_format='auto', add_page_nums=True,
                  add_bookmarks=True, fix_orientation=True,
                  prefer_sibling_pdf=True):
    """Master binding entrypoint (v3.1 - auto-installs Word fonts)."""
    # Iron Rule 5: ensure Word fonts are installed (auto from bundled fonts/)
    ensure_fonts_installed()
    # Iron Rule 3: sanitise appendix names
    appendix_list = sanitize_appendix_list(appendix_list)
    # Iron Rule 4: prefer manually-exported sibling PDF
    if prefer_sibling_pdf and is_docx(pleading_path):
        sib = str(Path(pleading_path).with_suffix('.pdf'))
        if os.path.exists(sib):
            print(f"\n-- Using sibling PDF {Path(sib).name} (preserves Word export) --")
            pleading_path = sib

    temp_dir = tempfile.mkdtemp(prefix='bind_')
    try:
        pleading_path, appendix_files, preprocess_report = preprocess_files(
            pleading_path, appendix_files, temp_dir, fix_orientation=fix_orientation,
        )
        print("\n-- Pass 1: layout --")
        pleading_pages = count_pdf_pages(pleading_path)
        app_pages = [count_pdf_pages(p) for p in appendix_files]
        dummy = [{'id': a.get('id', get_appendix_id(i, style)),
                  'label': a.get('label', format_appendix_label(i, style)),
                  'name': a.get('name', ''), 'page': '?'}
                 for i, a in enumerate(appendix_list)]
        dummy_toc = os.path.join(temp_dir, 'dummy_toc.pdf')
        create_toc_pdf(dummy, dummy_toc, style=style, format_mode=toc_format)
        toc_pages = count_pdf_pages(dummy_toc)
        page_map = []
        cur = 1 + pleading_pages
        toc_start = cur
        cur += toc_pages
        for idx, (af, ai) in enumerate(zip(appendix_files, appendix_list)):
            aid = ai.get('id', get_appendix_id(idx, style))
            lbl = ai.get('label', format_appendix_label(idx, style))
            nm = ai.get('name', f'Appendix {aid}')
            n = app_pages[idx]
            cp = cur; cur += 1
            asn = cur; cur += n
            page_map.append({'index': idx, 'id': aid, 'label': lbl, 'name': nm,
                             'cover_page': cp, 'appendix_start': asn,
                             'appendix_end': asn + n - 1, 'num_pages': n, 'file': af})
        total_expected = cur - 1
        print("-- Pass 2: TOC + covers --")
        real = [{'id': e['id'], 'label': e['label'], 'name': e['name'],
                 'page': e['appendix_start']} for e in page_map]
        toc_p = os.path.join(temp_dir, 'toc.pdf')
        create_toc_pdf(real, toc_p, style=style, format_mode=toc_format)
        cov_p = os.path.join(temp_dir, 'covers.pdf')
        create_cover_pages_pdf(
            [{'id': e['id'], 'label': e['label'], 'name': e['name']} for e in page_map],
            cov_p, style=style,
        )
        cov_doc = fitz.open(cov_p)
        print("-- Merging --")
        merged = fitz.open()
        merged.insert_pdf(fitz.open(pleading_path))
        merged.insert_pdf(fitz.open(toc_p))
        for e in page_map:
            merged.insert_pdf(cov_doc, from_page=e['index'], to_page=e['index'])
            merged.insert_pdf(fitz.open(e['file']))
        cov_doc.close()
        mp = os.path.join(temp_dir, 'merged.pdf')
        merged.save(mp, garbage=4, deflate=True); merged.close()
        actual = count_pdf_pages(mp)
        if add_page_nums:
            print("-- Page numbers --"); add_page_numbers(mp, mp)
        if add_bookmarks:
            print("-- Bookmarks --"); add_bookmarks_to_pdf(mp, mp, page_map, pleading_pages, toc_start)
        shutil.copy(mp, output_path)
        size_mb = os.path.getsize(output_path) / 1024 / 1024
        print(f"\n-- Done: {actual} pages, {size_mb:.2f} MB --")
        return {
            'output_path': output_path, 'total_pages': actual,
            'expected_pages': total_expected, 'file_size_mb': round(size_mb, 2),
            'pleading_pages': pleading_pages, 'toc_page': toc_start,
            'appendix_count': len(appendix_list), 'style': style,
            'pages_match': actual == total_expected,
            'page_map': page_map, 'preprocess_report': preprocess_report,
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == '__main__':
    print("bind_pdf v3.1 - PyMuPDF + LibreOffice + auto-fonts")
