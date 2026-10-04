#!/usr/bin/env python3
"""Prepare transparent, tightly cropped special-livery aircraft artwork.

Usage:
    python3 scripts/prepare-special-liveries.py SOURCE_DIR OUTPUT_DIR

Only near-white pixels connected to the outer canvas are removed, preserving
enclosed white fuselage areas.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw


DEFAULT_THRESHOLD = 24
THRESHOLD_OVERRIDES: dict[str, int] = {}
BACKGROUND_MARKER = (0, 0, 0, 0)
MARGIN_RATIO = 0.015


def exterior_background(image: Image.Image, threshold: int) -> Image.Image:
    """Return an RGB image whose exterior-connected background is marked."""
    marked = image.convert("RGBA")
    width, height = marked.size
    corners = ((0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1))
    for corner in corners:
        if marked.getpixel(corner) != BACKGROUND_MARKER:
            ImageDraw.floodfill(marked, corner, BACKGROUND_MARKER, thresh=threshold)
    return marked


def prepare(source: Path, destination: Path, threshold: int) -> None:
    original = Image.open(source).convert("RGBA")
    marked = exterior_background(original, threshold)
    marked_pixels = marked.load()
    pixels = original.load()

    for y in range(original.height):
        for x in range(original.width):
            if marked_pixels[x, y] == BACKGROUND_MARKER:
                red, green, blue, _ = pixels[x, y]
                pixels[x, y] = (red, green, blue, 0)

    alpha_box = original.getchannel("A").getbbox()
    if not alpha_box:
        raise ValueError(f"No aircraft artwork remained after processing {source.name}")

    left, top, right, bottom = alpha_box
    artwork_width = right - left
    margin = max(2, round(artwork_width * MARGIN_RATIO))
    artwork = original.crop((left, top, right, bottom))
    cropped = Image.new(
        "RGBA",
        (artwork.width + margin * 2, artwork.height + margin * 2),
        (255, 255, 255, 0),
    )
    cropped.alpha_composite(artwork, (margin, margin))
    destination.parent.mkdir(parents=True, exist_ok=True)
    cropped.save(destination, "WEBP", lossless=True, method=6, exact=True)
    print(
        f"{source.name} -> {destination.name} "
        f"({cropped.width}x{cropped.height}, threshold={threshold})"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sources = sorted(args.source_dir.glob("*.png"), key=lambda path: path.name.casefold())
    if not sources:
        raise SystemExit(f"No PNG files found in {args.source_dir}")

    for source in sources:
        threshold = THRESHOLD_OVERRIDES.get(source.name, DEFAULT_THRESHOLD)
        prepare(source, args.output_dir / f"{source.stem}.webp", threshold)


if __name__ == "__main__":
    main()
