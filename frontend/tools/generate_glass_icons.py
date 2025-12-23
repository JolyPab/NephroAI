#!/usr/bin/env python3
"""Generate Liquid Glass themed favicons and PWA icons."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIR = ROOT / "public"
ICON_DIR = PUBLIC_DIR / "icons"
ICON_DIR.mkdir(parents=True, exist_ok=True)

MASTER_SIZE = 1024
PNG_SIZES = [72, 96, 128, 144, 152, 192, 384, 512]
FAVICON_SIZES = [16, 32, 48, 64]


def lerp(color_a: tuple[int, int, int], color_b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(a + (b - a) * t) for a, b in zip(color_a, color_b))


def vertical_gradient(size: int, top_color: tuple[int, int, int], bottom_color: tuple[int, int, int]) -> Image.Image:
    gradient = Image.new("RGB", (1, size))
    for y in range(size):
        t = y / (size - 1)
        gradient.putpixel((0, y), lerp(top_color, bottom_color, t))
    return gradient.resize((size, size), Image.Resampling.BILINEAR)


def make_background(size: int) -> Image.Image:
    bg = vertical_gradient(size, (15, 18, 32), (26, 31, 51))
    bg = bg.convert("RGBA")

    noise = Image.effect_noise((size, size), 48).convert("L")
    noise = ImageOps.autocontrast(noise)
    noise_alpha = noise.point(lambda v: int(32 + (v - 128) * 0.25))
    noise_rgba = Image.merge("RGBA", (noise, noise, noise, noise_alpha))
    bg = ImageChops.screen(bg, noise_rgba)

    vignette = Image.new("L", (size, size), color=255)
    draw_vignette = ImageDraw.Draw(vignette)
    draw_vignette.ellipse(
        (
            size * -0.15,
            size * -0.15,
            size * 1.15,
            size * 1.15,
        ),
        fill=0,
    )
    vignette = vignette.filter(ImageFilter.GaussianBlur(radius=size * 0.18))
    vignette_rgba = Image.merge("RGBA", (vignette, vignette, vignette, vignette))
    bg = ImageChops.subtract(bg, vignette_rgba)

    return bg


def droplet_path(size: int) -> list[tuple[float, float]]:
    c = size / 2
    top = size * 0.17
    upper = size * 0.32
    mid = size * 0.58
    lower = size * 0.92
    width_top = size * 0.18
    width_mid = size * 0.28
    width_lower = size * 0.22

    return [
        (c, top),
        (c + width_top, upper),
        (c + width_mid, mid * 0.95),
        (c + width_lower, lower * 0.92),
        (c, lower),
        (c - width_lower, lower * 0.92),
        (c - width_mid, mid * 0.95),
        (c - width_top, upper),
    ]


def make_droplet(size: int, mask: Image.Image) -> Image.Image:
    drop = vertical_gradient(size, (145, 196, 255), (60, 105, 219)).convert("RGBA")
    drop = Image.composite(drop, Image.new("RGBA", (size, size), (0, 0, 0, 0)), mask)

    highlight = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw_highlight = ImageDraw.Draw(highlight)
    highlight_bbox = (
        size * 0.34,
        size * 0.28,
        size * 0.64,
        size * 0.50,
    )
    draw_highlight.ellipse(highlight_bbox, fill=(255, 255, 255, 160))
    highlight = highlight.filter(ImageFilter.GaussianBlur(radius=size * 0.05))
    drop = Image.alpha_composite(drop, highlight)

    rim_light = mask.filter(ImageFilter.GaussianBlur(radius=size * 0.03))
    rim = Image.merge(
        "RGBA",
        (
            rim_light,
            rim_light.point(lambda v: int(v * 0.85)),
            rim_light.point(lambda v: int(v * 0.45)),
            rim_light.point(lambda v: int(v * 0.6)),
        ),
    )
    drop = Image.alpha_composite(drop, rim)

    specular = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    spec_draw = ImageDraw.Draw(specular)
    spec_draw.line(
        [
            (size * 0.42, size * 0.38),
            (size * 0.53, size * 0.58),
        ],
        fill=(255, 255, 255, 110),
        width=max(1, size // 40),
    )
    specular = specular.filter(ImageFilter.GaussianBlur(radius=size * 0.02))
    drop = Image.alpha_composite(drop, specular)

    return drop


def make_glow(size: int, mask: Image.Image) -> Image.Image:
    glow = mask.filter(ImageFilter.GaussianBlur(radius=size * 0.09))
    glow = glow.point(lambda v: int(v * 0.5))
    glow = Image.merge(
        "RGBA",
        (
            glow.point(lambda v: int(118 * v / 255)),
            glow.point(lambda v: int(168 * v / 255)),
            glow.point(lambda v: int(255 * v / 255)),
            glow,
        ),
    )
    return glow


def build_master_icon() -> Image.Image:
    size = MASTER_SIZE

    bg = make_background(size)
    path = droplet_path(size)

    mask = Image.new("L", (size, size), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.polygon(path, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=size * 0.02))

    drop = make_droplet(size, mask)
    glow = make_glow(size, mask)

    shadow = mask.filter(ImageFilter.GaussianBlur(radius=size * 0.08))
    shadow = shadow.point(lambda v: int(v * 0.45))
    shadow_rgba = Image.merge("RGBA", (shadow, shadow, shadow, shadow))
    shadow_rgba = ImageChops.offset(shadow_rgba, 0, int(size * 0.03))

    layer = Image.alpha_composite(bg, shadow_rgba)
    layer = Image.alpha_composite(layer, glow)
    layer = Image.alpha_composite(layer, drop)
    return layer


def save_png_variants(master: Image.Image) -> None:
    for size in PNG_SIZES:
        resized = master.resize((size, size), Image.Resampling.LANCZOS)
        path = ICON_DIR / f"icon-{size}x{size}.png"
        resized.save(path, format="PNG")
        print(f"Saved {path.relative_to(ROOT)}")


def save_favicon(master: Image.Image) -> None:
    favicon_path = PUBLIC_DIR / "favicon.ico"
    master.save(favicon_path, format="ICO", sizes=[(s, s) for s in FAVICON_SIZES])
    print(f"Saved {favicon_path.relative_to(ROOT)}")


def main() -> None:
    master = build_master_icon()
    save_png_variants(master)
    save_favicon(master)


if __name__ == "__main__":
    main()
