#!/usr/bin/env python3
"""Generate BetaBrite Controller application icons from one deterministic design."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
RASTER_SIZES = (16, 32, 48, 64, 128, 256, 512)
MASTER_SIZE = 1024
LED_PATTERN = (
    "11110",
    "10001",
    "10001",
    "11110",
    "10001",
    "10001",
    "11110",
)


def svg_source() -> str:
    """Return the editable vector source for the application mark."""
    leds: list[str] = []
    for row, pattern in enumerate(LED_PATTERN):
        for column, enabled in enumerate(pattern):
            if enabled == "1":
                x = 174 + column * 98
                y = 190 + row * 93
                leds.append(
                    f'    <circle cx="{x}" cy="{y}" r="27" fill="#ffb21a"/>'
                )

    return "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">',
            '  <rect width="1024" height="1024" rx="190" fill="#10141d"/>',
            '  <rect x="54" y="54" width="916" height="916" rx="145" '
            'fill="none" stroke="#526274" stroke-width="28"/>',
            '  <rect x="112" y="112" width="800" height="800" rx="92" '
            'fill="#19170f" stroke="#303a47" stroke-width="24"/>',
            '  <g aria-label="amber LED letter B">',
            *leds,
            '  </g>',
            '  <rect x="720" y="214" width="116" height="116" rx="35" '
            'fill="#31d6a1"/>',
            '  <circle cx="778" cy="478" r="54" fill="#6e7c8e"/>',
            '  <circle cx="778" cy="638" r="54" fill="#6e7c8e"/>',
            '  <path d="M742 795h72m-36-36v72" fill="none" stroke="#31d6a1" '
            'stroke-width="34" stroke-linecap="round"/>',
            '</svg>',
            '',
        ]
    )


def render_master() -> Image.Image:
    """Render the mark at high resolution before downsampling."""
    image = Image.new("RGBA", (MASTER_SIZE, MASTER_SIZE), "#10141d")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (54, 54, 970, 970),
        radius=145,
        outline="#526274",
        width=28,
    )
    draw.rounded_rectangle(
        (112, 112, 912, 912),
        radius=92,
        fill="#19170f",
        outline="#303a47",
        width=24,
    )

    for row, pattern in enumerate(LED_PATTERN):
        for column, enabled in enumerate(pattern):
            if enabled == "1":
                x = 174 + column * 98
                y = 190 + row * 93
                draw.ellipse((x - 27, y - 27, x + 27, y + 27), fill="#ffb21a")

    draw.rounded_rectangle((720, 214, 836, 330), radius=35, fill="#31d6a1")
    draw.ellipse((724, 424, 832, 532), fill="#6e7c8e")
    draw.ellipse((724, 584, 832, 692), fill="#6e7c8e")
    draw.line((742, 795, 814, 795), fill="#31d6a1", width=34)
    draw.line((778, 759, 778, 831), fill="#31d6a1", width=34)
    return image


def output_paths(root: Path) -> tuple[Path, ...]:
    pngs = tuple(
        root / "assets" / "icons" / f"betabrite-controller-{size}.png"
        for size in RASTER_SIZES
    )
    return (
        root / "assets" / "betabrite-controller.svg",
        *pngs,
        root / "assets" / "betabrite-controller.ico",
        root / "assets" / "betabrite-controller.icns",
        root
        / "betabrite_controller"
        / "assets"
        / "betabrite-controller.png",
        root
        / "packaging"
        / "linux"
        / "dev.grubbs.BetaBriteController.png",
    )


def generate(root: Path) -> tuple[Path, ...]:
    """Write all source and platform icon assets below *root*."""
    for path in output_paths(root):
        path.parent.mkdir(parents=True, exist_ok=True)

    svg_path = root / "assets" / "betabrite-controller.svg"
    svg_path.write_text(svg_source(), encoding="utf-8")

    master = render_master()
    resized: dict[int, Image.Image] = {}
    for size in RASTER_SIZES:
        resized[size] = master.resize((size, size), Image.Resampling.LANCZOS)
        resized[size].save(
            root / "assets" / "icons" / f"betabrite-controller-{size}.png",
            format="PNG",
            optimize=True,
        )

    master.save(
        root / "assets" / "betabrite-controller.ico",
        format="ICO",
        sizes=[(size, size) for size in RASTER_SIZES if size <= 256],
    )
    master.save(root / "assets" / "betabrite-controller.icns", format="ICNS")
    resized[512].save(
        root
        / "betabrite_controller"
        / "assets"
        / "betabrite-controller.png",
        format="PNG",
        optimize=True,
    )
    resized[256].save(
        root
        / "packaging"
        / "linux"
        / "dev.grubbs.BetaBriteController.png",
        format="PNG",
        optimize=True,
    )
    return output_paths(root)


def check(root: Path) -> bool:
    """Return whether committed assets match a fresh generation exactly."""
    with tempfile.TemporaryDirectory(prefix="betabrite-icons-") as temporary:
        generated_root = Path(temporary)
        generate(generated_root)
        mismatches: list[str] = []
        for expected in output_paths(root):
            relative = expected.relative_to(root)
            actual = generated_root / relative
            if not expected.is_file() or expected.read_bytes() != actual.read_bytes():
                mismatches.append(str(relative))

    if mismatches:
        print("Generated icon assets are stale:")
        for mismatch in mismatches:
            print(f"  {mismatch}")
        return False
    print("Generated icon assets are current.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify that committed assets match a fresh deterministic generation.",
    )
    args = parser.parse_args()

    if args.check:
        return 0 if check(ROOT) else 1

    paths = generate(ROOT)
    print("Generated application branding:")
    for path in paths:
        print(f"  {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
