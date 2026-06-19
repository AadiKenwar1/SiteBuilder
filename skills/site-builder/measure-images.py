#!/usr/bin/env python3
"""
measure-images.py — Measure every image in a business's images/ folder so the
layout is built around the REAL aspect ratios, not guessed ones.

Why this exists:
    Declaring wrong width/height on a gallery/hero image (e.g. dropping a square
    photo into a landscape slot) produces hard crops and uneven grid rows. Run
    this FIRST and let the dims drive the gallery/hero layout choice.

Usage:
    python3 measure-images.py <images_dir>
    python3 measure-images.py businesses/<slug>/images

Output:
    One line per image: dimensions, aspect ratio, orientation, a low-res flag,
    and the exact width/height attrs to paste into <img>. Ends with a layout
    hint based on the mix of orientations found.
"""

import sys
import argparse
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow not installed. Run: pip install Pillow")

# Below this on the long edge, a photo looks soft when used full-bleed.
LOWRES_EDGE = 1000

EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".avif"}


def orientation(w, h):
    if w == h:
        return "square"
    return "landscape" if w > h else "portrait"


def main():
    ap = argparse.ArgumentParser(description="Measure images before building layout.")
    ap.add_argument("images_dir", help="path to a business's images/ folder")
    args = ap.parse_args()

    d = Path(args.images_dir)
    if not d.is_dir():
        sys.exit(f"Not a directory: {d}")

    files = sorted(p for p in d.iterdir() if p.suffix.lower() in EXTS)
    if not files:
        print(f"No images in {d}. Design with type/color/CSS instead "
              "(see SKILL.md), or generate an asset via canvas-design.")
        return

    counts = {"square": 0, "portrait": 0, "landscape": 0}
    lowres = []

    print(f"\n{len(files)} image(s) in {d}\n")
    print(f"  {'file':<16}{'size':<12}{'ratio':<8}{'orient':<11}{'note'}")
    print(f"  {'-'*16}{'-'*12}{'-'*8}{'-'*11}{'-'*20}")

    for f in files:
        try:
            with Image.open(f) as im:
                w, h = im.size
        except Exception as e:  # noqa: BLE001
            print(f"  {f.name:<16}ERROR  {e}")
            continue

        ori = orientation(w, h)
        counts[ori] += 1
        ratio = w / h
        note = ""
        if max(w, h) < LOWRES_EDGE:
            note = f"LOW-RES (<{LOWRES_EDGE}px) - avoid full-bleed"
            lowres.append(f.name)
        print(f"  {f.name:<16}{f'{w}x{h}':<12}{ratio:<8.2f}{ori:<11}{note}")
        print(f"  {'':<16}-> <img ... width=\"{w}\" height=\"{h}\">")

    # Layout hint based on the orientation mix.
    n = sum(counts.values())
    print("\nLayout hint:")
    if counts["portrait"] and counts["landscape"]:
        print("  Mixed portrait + landscape. Use masonry (CSS column-count) or "
              "give each <figure> its own aspect-ratio. Do NOT force one fixed "
              "grid cell ratio - that crops the odd ones out.")
    elif counts["portrait"] == n:
        print("  All portrait. A clean equal-column grid works; tall cards.")
    elif counts["landscape"] == n:
        print("  All landscape. Equal-column grid or a wide hero band works.")
    elif counts["square"] == n:
        print("  All square. Uniform square grid is safe.")
    else:
        print("  Square mixed with one other orientation. Masonry "
              "(column-count) keeps natural ratios without cropping.")

    if lowres:
        print(f"\n  {len(lowres)} low-res: {', '.join(lowres)} - keep small "
              "(thumb/inline), don't use as a full-bleed hero/background.")
    print()


if __name__ == "__main__":
    main()
