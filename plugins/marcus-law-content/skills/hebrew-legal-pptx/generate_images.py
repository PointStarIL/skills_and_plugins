# -*- coding: utf-8 -*-
"""יצירת 6 תמונות AI לשקפים 1, 4, 5, 6, 8, 9 - ספציפיות לתוכן כל שקף."""

import sys
from pathlib import Path

SKILL_DIR = "/sessions/festive-pensive-meitner/mnt/.claude/skills/hebrew-legal-pptx"
sys.path.insert(0, str(Path(SKILL_DIR) / "scripts"))

from image_generator import generate_image

OUT_DIR = Path("/sessions/festive-pensive-meitner/mnt/outputs/images")
OUT_DIR.mkdir(parents=True, exist_ok=True)

prompts = {
    "slide1_opening.png": {
        "aspect": "1:1",
        "prompt": (
            "Modern minimalist illustration for a legal lecture about judicial review of "
            "urban planning decisions. Show a stylized judicial gavel resting on top of "
            "architectural blueprints, with a small city skyline silhouette of layered "
            "rooftops and buildings in the background. Deep navy blue and warm gold accents, "
            "cream beige background. Sophisticated legal-architectural style, clean lines, "
            "no text, no labels, no Hebrew letters, no writing of any kind."
        ),
    },
    "slide4_stages.png": {
        "aspect": "1:1",
        "prompt": (
            "Modern minimalist illustration showing the stages of a planning approval process "
            "as a vertical timeline. Four icons connected by a thin line: a folded blueprint "
            "document at top, three small human silhouettes raising hands (objections), a "
            "judicial gavel, and an official stamp at bottom. Deep navy blue and warm gold "
            "accents, cream background, clean infographic style, "
            "no text, no labels, no Hebrew letters, no writing of any kind."
        ),
    },
    "slide5_petitioners.png": {
        "aspect": "1:1",
        "prompt": (
            "Modern minimalist illustration of three diverse human silhouettes standing "
            "together, holding folded documents, with arms slightly raised in protest. "
            "They face a stylized municipal planning building with classical columns. "
            "Deep navy blue and warm gold accents, cream background, "
            "professional editorial style, no text, no labels, no Hebrew letters, "
            "no writing of any kind."
        ),
    },
    "slide6_respondents.png": {
        "aspect": "1:1",
        "prompt": (
            "Modern minimalist illustration of a panel of three formally seated official "
            "figures behind a long wooden bench, with a stylized planning institution "
            "building visible behind them. Government officials reviewing a document. "
            "Deep navy blue and warm gold accents, cream background, professional "
            "editorial style, no text, no labels, no Hebrew letters, no writing of any kind."
        ),
    },
    "slide8_jurisdiction.png": {
        "aspect": "1:1",
        "prompt": (
            "Modern minimalist illustration showing a judicial gavel resting on a stack of "
            "law books, with an architectural blueprint partially visible underneath. A "
            "stylized scales of justice icon balances above, suggesting subject-matter "
            "authority. Deep navy blue and warm gold accents, cream background, clean "
            "editorial style, no text, no labels, no Hebrew letters, no writing of any kind."
        ),
    },
    "slide9_local.png": {
        "aspect": "1:1",
        "prompt": (
            "Modern minimalist illustration of a stylized geographic territorial map with "
            "subtle outlined regions, a single prominent location pin marker placed on it, "
            "and a small classical courthouse icon nearby. Concept of territorial "
            "jurisdiction by location. Deep navy blue and warm gold accents, cream "
            "background, clean infographic style, no text, no labels, no Hebrew letters, "
            "no writing of any kind."
        ),
    },
}

for filename, spec in prompts.items():
    out_path = OUT_DIR / filename
    if out_path.exists():
        print(f"SKIP (exists): {filename}")
        continue
    print(f"Generating: {filename} ({spec['aspect']})...")
    try:
        result = generate_image(
            prompt=spec["prompt"],
            aspect_ratio=spec["aspect"],
            model="google/imagen4-fast",
            output_dir=str(OUT_DIR),
            filename=filename,
        )
        print(f"  -> {result}")
    except Exception as e:
        print(f"  ERROR: {e}")

print("\nDone.")
print("Generated files:")
for f in sorted(OUT_DIR.glob("*.png")):
    print(f"  {f.name}: {f.stat().st_size} bytes")
