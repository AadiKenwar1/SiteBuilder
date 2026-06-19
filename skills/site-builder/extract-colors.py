#!/usr/bin/env python3
"""
extract-colors.py — Extract a brand color palette from a logo image.

Usage:
    python3 extract-colors.py <image_path> [--count 5]

Output:
    Prints a JSON block + ready-to-paste CSS custom properties.
    Claude reads the output and uses it as the site's color palette.
"""

import sys
import json
import argparse
from pathlib import Path


def luminance(r, g, b):
    """Relative luminance per WCAG 2.1."""
    def channel(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_ratio(l1, l2):
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def hex_color(rgb):
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def classify(rgb):
    """Classify a color as light/dark and warm/cool."""
    r, g, b = rgb
    lum = luminance(r, g, b)
    tone = "light" if lum > 0.35 else "dark" if lum < 0.1 else "mid"

    # Warm if red+yellow dominates, cool if blue+green dominates
    warmth = (r + g * 0.5) - (b + g * 0.5)
    temp = "warm" if warmth > 20 else "cool" if warmth < -20 else "neutral"

    return tone, temp, round(lum, 3)


def suggest_text_color(bg_rgb):
    """Return black or white, whichever contrasts better with the background."""
    lum = luminance(*bg_rgb)
    white_contrast = contrast_ratio(1.0, lum)
    black_contrast = contrast_ratio(0.0, lum)
    return "#FFFFFF" if white_contrast >= black_contrast else "#111111"


def build_palette(colors):
    """
    Assign semantic roles to extracted colors.
    Tries to pick a strong primary, a contrasting accent, and safe neutrals.
    """
    annotated = []
    for c in colors:
        tone, temp, lum = classify(c)
        annotated.append({"rgb": c, "hex": hex_color(c), "tone": tone, "temp": temp, "lum": lum})

    # Sort by luminance ascending (darkest first)
    by_lum = sorted(annotated, key=lambda x: x["lum"])

    # Primary: most saturated mid-tone, or fallback to darkest
    def saturation(rgb):
        r, g, b = [x / 255 for x in rgb]
        return max(r, g, b) - min(r, g, b)

    mids = [a for a in annotated if a["tone"] == "mid"] or annotated
    primary = max(mids, key=lambda a: saturation(a["rgb"]))

    # Accent: highest saturation that isn't the primary
    remainder = [a for a in annotated if a["hex"] != primary["hex"]]
    accent = max(remainder, key=lambda a: saturation(a["rgb"])) if remainder else primary

    # Background: lightest color, or fabricate near-white if none are light
    lights = [a for a in by_lum if a["tone"] == "light"]
    background = lights[-1] if lights else {"hex": "#F8F8F6", "rgb": (248, 248, 246)}

    # Surface: second lightest, or a tint of primary
    surface_candidates = [a for a in by_lum if a["hex"] not in (background["hex"], primary["hex"])]
    surface = surface_candidates[-1] if surface_candidates else {"hex": "#FFFFFF", "rgb": (255, 255, 255)}

    # Text: darkest extracted color or fabricated near-black
    darks = [a for a in by_lum if a["tone"] == "dark"]
    text = darks[0] if darks else {"hex": "#111111", "rgb": (17, 17, 17)}

    return {
        "primary":    {"hex": primary["hex"],    "on": suggest_text_color(primary["rgb"])},
        "accent":     {"hex": accent["hex"],     "on": suggest_text_color(accent["rgb"])},
        "background": {"hex": background["hex"], "on": suggest_text_color(background["rgb"])},
        "surface":    {"hex": surface["hex"],    "on": suggest_text_color(surface["rgb"])},
        "text":       {"hex": text["hex"]},
        "all_extracted": [a["hex"] for a in annotated],
    }


def main():
    parser = argparse.ArgumentParser(description="Extract brand colors from a logo image.")
    parser.add_argument("image", help="Path to logo image (PNG, JPG, WEBP, etc.)")
    parser.add_argument("--count", type=int, default=6, help="Number of colors to extract (default: 6)")
    args = parser.parse_args()

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Error: file not found: {image_path}", file=sys.stderr)
        sys.exit(1)

    try:
        from colorthief import ColorThief
    except ImportError:
        print("Error: colorthief not installed. Run: pip install colorthief", file=sys.stderr)
        sys.exit(1)

    try:
        ct = ColorThief(str(image_path))
        colors = ct.get_palette(color_count=args.count, quality=1)
    except Exception as e:
        print(f"Error extracting colors: {e}", file=sys.stderr)
        sys.exit(1)

    palette = build_palette(colors)

    # --- JSON output (for Claude to parse) ---
    print("\n=== COLOR PALETTE (JSON) ===")
    print(json.dumps(palette, indent=2))

    # --- CSS custom properties (ready to paste) ---
    print("\n=== CSS CUSTOM PROPERTIES ===")
    print(":root {")
    print(f"  --color-primary:    {palette['primary']['hex']};")
    print(f"  --color-on-primary: {palette['primary']['on']};")
    print(f"  --color-accent:     {palette['accent']['hex']};")
    print(f"  --color-on-accent:  {palette['accent']['on']};")
    print(f"  --color-bg:         {palette['background']['hex']};")
    print(f"  --color-surface:    {palette['surface']['hex']};")
    print(f"  --color-text:       {palette['text']['hex']};")
    print("}")

    print("\n=== NOTES FOR CLAUDE ===")
    print("- Use --color-primary for nav background, hero background, and main CTAs.")
    print("- Use --color-accent for buttons, highlights, and hover states.")
    print("- Use --color-bg as the page background.")
    print("- Use --color-surface for cards and section alternates.")
    print("- Use --color-text for all body copy.")
    print("- --color-on-primary / --color-on-accent are the correct text colors on those backgrounds.")
    print(f"- All extracted colors: {', '.join(palette['all_extracted'])}")
    print("- If the palette feels flat, darken --color-primary by 15% for hover states.")


if __name__ == "__main__":
    main()
