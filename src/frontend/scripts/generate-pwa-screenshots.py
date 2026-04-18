"""
Generate PWA manifest screenshots (Chrome installability / richer install UI).
Run from repo: python src/frontend/scripts/generate-pwa-screenshots.py
Requires Pillow: pip install pillow
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public" / "screenshots"


def _draw_frame(img: Image.Image, title: str, subtitle: str) -> None:
    draw = ImageDraw.Draw(img)
    w, h = img.size
    # Soft vignette bar (app chrome hint)
    bar_h = max(48, h // 14)
    draw.rectangle((0, 0, w, bar_h), fill=(15, 23, 42))
    try:
        font_t = ImageFont.truetype("arial.ttf", max(18, w // 42))
        font_s = ImageFont.truetype("arial.ttf", max(14, w // 52))
    except OSError:
        font_t = ImageFont.load_default()
        font_s = ImageFont.load_default()
    draw.text((24, bar_h // 3), title, fill=(248, 250, 252), font=font_t)
    draw.text((24, h - h // 8), subtitle, fill=(148, 163, 184), font=font_s)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # narrow: mobile / standard install prompt path
    narrow = Image.new("RGB", (540, 720), (15, 23, 42))
    _draw_frame(narrow, "LexMatePH", "Philippine law companion · SC decisions, codals, LexPlay")
    n_path = OUT / "pwa-narrow.png"
    narrow.save(n_path, format="PNG", optimize=True)
    print("Wrote", n_path, narrow.size)

    # wide: desktop richer install UI
    wide = Image.new("RGB", (1280, 720), (15, 23, 42))
    _draw_frame(wide, "LexMatePH", "Case digest, bar questions, codals — install for offline-ready study")
    w_path = OUT / "pwa-wide.png"
    wide.save(w_path, format="PNG", optimize=True)
    print("Wrote", w_path, wide.size)


if __name__ == "__main__":
    main()
