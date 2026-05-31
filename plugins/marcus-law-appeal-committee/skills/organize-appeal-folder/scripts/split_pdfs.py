#!/usr/bin/env python3
"""
PDF Splitter for Appeal Case Files
Splits appeal documents (כתבי טענות) into main pleading + appendices.

Usage:
    python split_pdfs.py <base_folder> <splits_json>

Where splits_json is a JSON file with structure:
[
    {
        "source": "filename.pdf",
        "subfolder": "subfolder name",
        "parts": [
            [1, 3, "output_name.pdf"],
            [4, 10, "another_output.pdf"]
        ]
    }
]

Pages are 1-indexed, inclusive.
"""

import os
import sys
import json
from PyPDF2 import PdfReader, PdfWriter


def split_pdf(source_path, output_folder, parts):
    """Split a single PDF into multiple files based on page ranges."""
    if not os.path.exists(source_path):
        print(f"  ERROR: File not found: {os.path.basename(source_path)}")
        return False

    reader = PdfReader(source_path)
    total_pages = len(reader.pages)
    print(f"  Total pages: {total_pages}")

    os.makedirs(output_folder, exist_ok=True)

    for start, end, out_name in parts:
        if end > total_pages:
            print(f"  Warning: page {end} exceeds {total_pages}, adjusting")
            end = total_pages

        writer = PdfWriter()
        for page_num in range(start - 1, end):
            writer.add_page(reader.pages[page_num])

        out_path = os.path.join(output_folder, out_name)
        with open(out_path, "wb") as f:
            writer.write(f)

        size_kb = os.path.getsize(out_path) / 1024
        print(f"  OK: {out_name} (pp {start}-{end}, {size_kb:.0f} KB)")

    return True


def main():
    if len(sys.argv) < 3:
        print("Usage: python split_pdfs.py <base_folder> <splits_json>")
        sys.exit(1)

    base_folder = sys.argv[1]
    splits_file = sys.argv[2]

    with open(splits_file, "r", encoding="utf-8") as f:
        splits = json.load(f)

    print(f"Processing {len(splits)} documents from: {base_folder}\n")

    for split_info in splits:
        source = os.path.join(base_folder, split_info["source"])
        subfolder = os.path.join(base_folder, split_info["subfolder"])

        print(f"{'='*50}")
        print(f"Source: {split_info['source']}")
        print(f"Target: {split_info['subfolder']}/")

        parts = [(p[0], p[1], p[2]) for p in split_info["parts"]]
        split_pdf(source, subfolder, parts)

    print(f"\n{'='*50}")
    print("Done! Summary:\n")

    for split_info in splits:
        subfolder = os.path.join(base_folder, split_info["subfolder"])
        if os.path.exists(subfolder):
            files = sorted(os.listdir(subfolder))
            print(f"  {split_info['subfolder']}/")
            for f in files:
                fpath = os.path.join(subfolder, f)
                size_kb = os.path.getsize(fpath) / 1024
                print(f"    {f} ({size_kb:.0f} KB)")
            print()


if __name__ == "__main__":
    main()
