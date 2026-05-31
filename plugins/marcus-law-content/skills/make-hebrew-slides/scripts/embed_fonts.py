"""
מטמיע פונטים TTF בתוך קובץ PPTX.

PowerPoint תומך בהטמעת פונטים דרך:
1. הוספת קבצי TTF לתוך ppt/fonts/ ב-ZIP
2. רישום ה-MIME type ב-[Content_Types].xml
3. הוספת relationships ב-ppt/_rels/presentation.xml.rels
4. הוספת <p:embeddedFontLst> ב-ppt/presentation.xml

usage:
    embed_fonts(
        pptx_path="/path/to/deck.pptx",
        fonts={
            "Suez One": {"regular": "/path/to/SuezOne-Regular.ttf"},
            "Rubik": {
                "regular": "/path/to/Rubik-Regular.ttf",
                "bold": "/path/to/Rubik-Bold.ttf",
            },
        },
    )
"""
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
import re

NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
}

FONT_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/font"
FONT_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.obfuscatedFont"


def _read_zip_to_dir(src: str, work: Path) -> None:
    work.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src, "r") as zf:
        zf.extractall(work)


def _zip_dir_to_file(work: Path, dst: str) -> None:
    # Write to a temp path in /tmp (always unlink-able), then copy bytes over
    # to dst (which may live on a mount that doesn't allow unlink).
    import tempfile, os
    fd, tmp = tempfile.mkstemp(prefix="embed_fonts_", suffix=".pptx")
    os.close(fd)
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(work.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(work).as_posix())
    Path(dst).write_bytes(Path(tmp).read_bytes())
    try:
        Path(tmp).unlink()
    except Exception:
        pass


def _obfuscate_font(ttf_bytes: bytes, guid_str: str) -> bytes:
    """
    PowerPoint דורש פונטים מוסתרים: 32 הבייטים הראשונים מוצפנים ב-XOR
    עם מפתח שנגזר מ-GUID של הפונט. ראה ECMA-376 Part 1, §15.2.13.
    """
    # GUID format: {XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}
    g = guid_str.strip("{}").replace("-", "")
    # The key is the GUID bytes in reverse order for the first 16 bytes,
    # then repeated for the second 16. Simpler: 16-byte key, applied twice.
    if len(g) != 32:
        raise ValueError(f"bad guid: {guid_str}")
    # Each pair of hex chars is one byte; reverse the *byte order*.
    key_bytes = bytes(int(g[i:i+2], 16) for i in range(0, 32, 2))
    # The OOXML spec says: reverse the first 16 bytes. Apply XOR over the
    # first 32 bytes of the font with key||key.
    key = key_bytes[::-1]  # reverse byte order
    full_key = key + key  # 32 bytes
    head = bytearray(ttf_bytes[:32])
    for i in range(32):
        head[i] ^= full_key[i]
    return bytes(head) + ttf_bytes[32:]


def embed_fonts(pptx_path: str, fonts: dict) -> str:
    """
    מטמיע פונטים בקובץ pptx קיים. מחזיר את הנתיב המעודכן (אותו קובץ).

    fonts: dict ממפה שם פונט (typeface) -> dict עם המפתחות:
        regular, bold, italic, boldItalic — כל אחד נתיב לקובץ TTF.
    """
    import tempfile
    pptx_path = str(pptx_path)
    work = Path(tempfile.mkdtemp(prefix="embed_fonts_"))
    _read_zip_to_dir(pptx_path, work)

    # 1. Generate stable per-font GUIDs and obfuscate fonts into ppt/fonts/
    fonts_dir = work / "ppt" / "fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)

    import uuid
    font_records = []  # list of {typeface, weight_to_filename}
    for typeface, weights in fonts.items():
        record = {"typeface": typeface, "weights": {}}
        for weight, ttf_path in weights.items():
            ttf_bytes = Path(ttf_path).read_bytes()
            guid = "{" + str(uuid.uuid4()).upper() + "}"
            obfuscated = _obfuscate_font(ttf_bytes, guid)
            safe_typeface = re.sub(r"[^A-Za-z0-9]+", "", typeface)
            fname = f"font_{safe_typeface}_{weight}.fntdata"
            (fonts_dir / fname).write_bytes(obfuscated)
            record["weights"][weight] = {"filename": fname, "guid": guid}
        font_records.append(record)

    # 2. Update [Content_Types].xml — add Default for fntdata
    ct_path = work / "[Content_Types].xml"
    ct_xml = ct_path.read_text(encoding="utf-8")
    if 'Extension="fntdata"' not in ct_xml:
        # Insert a new <Default> entry after the opening <Types ...>
        new_default = f'<Default Extension="fntdata" ContentType="{FONT_CONTENT_TYPE}"/>'
        ct_xml = ct_xml.replace("<Types ", "<Types ", 1)  # noop, but ensure
        # Add after the first <Default … or <Override
        # Simpler: inject right after the opening <Types ...>
        ct_xml = re.sub(
            r"(<Types[^>]*>)",
            r"\1" + new_default,
            ct_xml,
            count=1,
        )
        ct_path.write_text(ct_xml, encoding="utf-8")

    # 3. Add relationships in ppt/_rels/presentation.xml.rels
    rels_path = work / "ppt" / "_rels" / "presentation.xml.rels"
    rels_xml = rels_path.read_text(encoding="utf-8")
    # Find max existing rId
    existing_ids = [int(m.group(1)) for m in re.finditer(r'Id="rId(\d+)"', rels_xml)]
    next_id = max(existing_ids) + 1 if existing_ids else 1

    new_rel_entries = []
    for record in font_records:
        for weight, info in record["weights"].items():
            rid = f"rId{next_id}"
            next_id += 1
            info["rid"] = rid
            new_rel_entries.append(
                f'<Relationship Id="{rid}" '
                f'Type="{FONT_REL_TYPE}" '
                f'Target="fonts/{info["filename"]}"/>'
            )
    rels_xml = re.sub(
        r"(</Relationships>)",
        "".join(new_rel_entries) + r"\1",
        rels_xml,
        count=1,
    )
    rels_path.write_text(rels_xml, encoding="utf-8")

    # 4. Add <p:embeddedFontLst> to ppt/presentation.xml
    pres_path = work / "ppt" / "presentation.xml"
    pres_xml = pres_path.read_text(encoding="utf-8")

    weight_to_tag = {
        "regular": "p:regular",
        "bold": "p:bold",
        "italic": "p:italic",
        "boldItalic": "p:boldItalic",
    }

    parts = ["<p:embeddedFontLst>"]
    for record in font_records:
        parts.append("<p:embeddedFont>")
        parts.append(f'<p:font typeface="{record["typeface"]}" panose="020B0604020202020204" pitchFamily="34" charset="0"/>')
        for weight, info in record["weights"].items():
            tag = weight_to_tag.get(weight, "p:regular")
            parts.append(f'<{tag} r:id="{info["rid"]}"/>')
        parts.append("</p:embeddedFont>")
    parts.append("</p:embeddedFontLst>")
    embedded = "".join(parts)

    # Insert just before </p:presentation>; remove existing list if any
    pres_xml = re.sub(r"<p:embeddedFontLst>.*?</p:embeddedFontLst>", "", pres_xml, flags=re.DOTALL)
    # Insertion point: before <p:defaultTextStyle> if present, else before </p:presentation>
    if "<p:defaultTextStyle>" in pres_xml:
        pres_xml = pres_xml.replace("<p:defaultTextStyle>", embedded + "<p:defaultTextStyle>", 1)
    else:
        pres_xml = pres_xml.replace("</p:presentation>", embedded + "</p:presentation>", 1)

    pres_path.write_text(pres_xml, encoding="utf-8")

    # 5. Re-zip
    _zip_dir_to_file(work, pptx_path)
    shutil.rmtree(work)
    return pptx_path


if __name__ == "__main__":
    import sys
    p = sys.argv[1]
    fonts_dir = Path(__file__).parent / "fonts" / "ttf"
    embed_fonts(
        p,
        fonts={
            "Suez One": {"regular": str(fonts_dir / "SuezOne-Regular.ttf")},
            "Rubik": {
                "regular": str(fonts_dir / "Rubik-Regular.ttf"),
                "bold": str(fonts_dir / "Rubik-Bold.ttf"),
            },
        },
    )
    print(f"Embedded fonts in {p}")
