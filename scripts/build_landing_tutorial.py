from __future__ import annotations

from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "landing" / "tutorial"
OUTPUT = ASSET_DIR / "nephroai-tour.webp"
MOBILE_OUTPUT = ASSET_DIR / "nephroai-tour-mobile.webp"
CANVAS = (2000, 1367)
SCREEN_BOX = (90, 170, 1910, 1140)

SCENES = [
    (
        "01-inicio.png",
        "1 de 5 · Resumen",
        "Vea de inmediato su estado renal y los indicadores que requieren atención.",
    ),
    (
        "02-subir.png",
        "2 de 5 · Subir análisis",
        "Suba un PDF de laboratorio y NephroAI organizará los resultados.",
    ),
    (
        "03-graficos-egfr.png",
        "3 de 5 · Seguir tendencias",
        "Compare cada indicador y detecte valores fuera del rango de referencia.",
    ),
    (
        "04-ia.png",
        "4 de 5 · Preguntar a la IA",
        "Entienda qué cambió y qué conviene conversar con su médico.",
    ),
    (
        "05-consultas.png",
        "5 de 5 · Consultas",
        "Comparta sus resultados y gestione la comunicación con su médico.",
    ),
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    family = "segoeuib.ttf" if bold else "segoeui.ttf"
    path = Path("C:/Windows/Fonts") / family
    return ImageFont.truetype(str(path), size=size)


def rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=255)
    return mask


def fit_screen(image: Image.Image, max_height: int = 1000) -> Image.Image:
    left, top, right, bottom = SCREEN_BOX
    target = (right - left, bottom - top)
    image = image.convert("RGB")
    if image.height > max_height:
        image = image.crop((0, 0, image.width, max_height))
    image = ImageOps.contain(image, target, Image.Resampling.LANCZOS)
    stage = Image.new("RGB", target, "#ffffff")
    x = (target[0] - image.width) // 2
    y = (target[1] - image.height) // 2
    stage.paste(image, (x, y))
    stage.putalpha(rounded_mask(target, 40))
    return stage


def make_scene(filename: str, label: str, caption: str) -> Image.Image:
    canvas = Image.new("RGB", CANVAS, "#eef6ff")
    draw = ImageDraw.Draw(canvas)
    draw.text((90, 62), "NephroAI en menos de un minuto", font=font(52, True), fill="#071b46")
    label_font = font(34, True)
    label_box = draw.textbbox((0, 0), label, font=label_font)
    label_width = label_box[2] - label_box[0] + 50
    draw.rounded_rectangle((CANVAS[0] - label_width - 90, 57, CANVAS[0] - 90, 125), radius=34, fill="#dceaff")
    draw.text((CANVAS[0] - label_width - 65, 71), label, font=label_font, fill="#075be8")

    max_height = 844 if filename == "01-inicio.png" else 900 if filename == "03-graficos-egfr.png" else 1000
    screen = fit_screen(Image.open(ASSET_DIR / filename), max_height=max_height)
    canvas.paste(screen, (SCREEN_BOX[0], SCREEN_BOX[1]), screen)
    draw.rounded_rectangle((90, 1173, 1910, 1310), radius=37, fill="#071b46")
    draw.text((137, 1211), caption, font=font(40, True), fill="#ffffff")
    return canvas


def make_mobile_scene(filename: str, label: str, caption: str) -> Image.Image:
    canvas = Image.new("RGB", (1080, 1500), "#eef6ff")
    draw = ImageDraw.Draw(canvas)
    draw.text((48, 47), "NephroAI en menos de un minuto", font=font(45, True), fill="#071b46")
    draw.rounded_rectangle((48, 119, 1032, 194), radius=38, fill="#dceaff")
    draw.text((81, 137), label, font=font(35, True), fill="#075be8")

    image = Image.open(ASSET_DIR / filename).convert("RGB")
    max_height = 844 if filename == "01-inicio.png" else 900 if filename == "03-graficos-egfr.png" else 1000
    if image.height > max_height:
        image = image.crop((0, 0, image.width, max_height))
    image = ImageOps.contain(image, (984, 939), Image.Resampling.LANCZOS)
    stage = Image.new("RGB", (984, 939), "#ffffff")
    stage.paste(image, ((984 - image.width) // 2, (939 - image.height) // 2))
    stage.putalpha(rounded_mask(stage.size, 33))
    canvas.paste(stage, (48, 227), stage)

    draw.rounded_rectangle((48, 1205, 1032, 1436), radius=36, fill="#071b46")
    lines = wrap(caption, width=42)
    line_height = 63
    start_y = 1250 + max(0, (2 - len(lines)) * 27)
    for index, line in enumerate(lines[:3]):
        draw.text((87, start_y + index * line_height), line, font=font(47, True), fill="#ffffff")
    return canvas


def main() -> None:
    scenes = [make_scene(*scene) for scene in SCENES]
    frames = scenes
    durations = [4200] * len(scenes)

    frames[0].save(
        OUTPUT,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        quality=95,
        method=6,
    )
    mobile_frames = [make_mobile_scene(*scene) for scene in SCENES]
    mobile_frames[0].save(
        MOBILE_OUTPUT,
        save_all=True,
        append_images=mobile_frames[1:],
        duration=durations,
        loop=0,
        quality=95,
        method=6,
    )
    print(f"Created {OUTPUT} ({OUTPUT.stat().st_size / 1024 / 1024:.2f} MB)")
    print(f"Created {MOBILE_OUTPUT} ({MOBILE_OUTPUT.stat().st_size / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    main()
