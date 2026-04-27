from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

try:
    from moviepy import (
        AudioFileClip,
        CompositeVideoClip,
        ImageClip,
        VideoClip,
        VideoFileClip,
        concatenate_videoclips,
        vfx,
    )
except ImportError:  # MoviePy 1.x
    from moviepy.editor import (
        AudioFileClip,
        CompositeVideoClip,
        ImageClip,
        VideoClip,
        VideoFileClip,
        concatenate_videoclips,
        vfx,
    )


VIDEO_SIZE = (1080, 1920)
FPS = 30
CARTOON_FPS = 18
BACKGROUND = (12, 15, 22)
TEXT_COLOR = (245, 247, 250)
SUBTITLE_BOX = (8, 10, 16, 214)
MUTED = (155, 164, 178)
ACCENT_COLORS = [
    (85, 196, 255),
    (255, 190, 92),
    (131, 236, 164),
    (255, 132, 161),
    (182, 151, 255),
]


def _font_candidates(bold: bool = True) -> list[str]:
    if bold:
        return [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
        ]

    return [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial.ttf",
    ]


def _load_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for font_path in _font_candidates(bold=bold):
        if Path(font_path).exists():
            return ImageFont.truetype(font_path, size=size)
    return ImageFont.load_default()


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""

    for word in words:
        candidate = word if not current else f"{current} {word}"
        width, _ = _text_size(draw, candidate, font)

        if width <= max_width:
            current = candidate
            continue

        if current:
            lines.append(current)
            current = word
        else:
            lines.append(word)
            current = ""

    if current:
        lines.append(current)

    return lines or [text]


def _fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    max_height: int,
    max_font_size: int = 88,
    min_font_size: int = 42,
) -> tuple[ImageFont.ImageFont, list[str], int]:
    for font_size in range(max_font_size, min_font_size - 1, -2):
        font = _load_font(font_size, bold=True)
        lines = _wrap_text(draw, text, font, max_width)
        line_height = math.ceil(font_size * 1.18)
        total_height = line_height * len(lines)
        widest = max(_text_size(draw, line, font)[0] for line in lines)

        if widest <= max_width and total_height <= max_height:
            return font, lines, line_height

    font = _load_font(min_font_size, bold=True)
    lines = _wrap_text(draw, text, font, max_width)
    return font, lines, math.ceil(min_font_size * 1.18)


def _clip_with_duration(clip: Any, duration: float) -> Any:
    if hasattr(clip, "with_duration"):
        return clip.with_duration(duration)
    return clip.set_duration(duration)


def _clip_with_fps(clip: Any, fps: int) -> Any:
    if hasattr(clip, "with_fps"):
        return clip.with_fps(fps)
    return clip.set_fps(fps)


def _clip_with_audio(clip: Any, audio: Any) -> Any:
    if hasattr(clip, "with_audio"):
        return clip.with_audio(audio)
    return clip.set_audio(audio)


def _clip_with_start(clip: Any, start: float) -> Any:
    if hasattr(clip, "with_start"):
        return clip.with_start(start)
    return clip.set_start(start)


def _clip_with_position(clip: Any, position: tuple[str, str]) -> Any:
    if hasattr(clip, "with_position"):
        return clip.with_position(position)
    return clip.set_position(position)


def _apply_fades(clip: Any, fade_duration: float = 0.2) -> Any:
    try:
        if hasattr(clip, "with_effects") and hasattr(vfx, "FadeIn"):
            return clip.with_effects([vfx.FadeIn(fade_duration), vfx.FadeOut(fade_duration)])

        if hasattr(clip, "fx") and hasattr(vfx, "fadein") and hasattr(vfx, "fadeout"):
            return clip.fx(vfx.fadein, fade_duration).fx(vfx.fadeout, fade_duration)
    except Exception:
        return clip

    return clip


def _accent_from_prompt(scene_prompt: str) -> tuple[int, int, int]:
    digest = hashlib.sha256(scene_prompt.encode("utf-8")).digest()
    return ACCENT_COLORS[digest[0] % len(ACCENT_COLORS)]


def _create_local_background(scene_prompt: str, image_path: Path) -> Path:
    """Create a simple no-text visual placeholder for a scene provider fallback."""
    image_path.parent.mkdir(parents=True, exist_ok=True)

    image = Image.new("RGB", VIDEO_SIZE, BACKGROUND)
    draw = ImageDraw.Draw(image)
    accent = _accent_from_prompt(scene_prompt)

    draw.rectangle((0, 0, VIDEO_SIZE[0], VIDEO_SIZE[1]), fill=BACKGROUND)
    draw.rectangle((0, 0, VIDEO_SIZE[0], 18), fill=accent)
    draw.ellipse((720, 110, 1280, 670), outline=(28, 34, 48), width=8)
    draw.ellipse((-260, 1180, 360, 1800), outline=(28, 34, 48), width=8)
    draw.rounded_rectangle((120, 520, 960, 1300), radius=42, fill=(18, 23, 34))
    draw.rounded_rectangle((170, 610, 910, 910), radius=36, fill=(29, 36, 51))
    draw.rounded_rectangle((250, 1000, 830, 1110), radius=26, fill=accent)
    draw.rounded_rectangle((330, 1170, 750, 1240), radius=20, fill=(42, 50, 67))

    # Do not render prompt text here. Providers generate visuals only;
    # captions are composited later as controlled subtitles.
    image.save(image_path, quality=95)
    return image_path


def create_local_scene_video(
    scene_prompt: str,
    duration: int,
    output_path: str | Path,
) -> str:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    image_path = output_path.with_suffix(".png")
    _create_local_background(scene_prompt, image_path)

    clip = None
    try:
        clip = ImageClip(str(image_path))
        clip = _clip_with_duration(clip, float(duration))
        clip = _clip_with_fps(clip, FPS)
        clip = _apply_fades(clip)
        clip.write_videofile(
            str(output_path),
            fps=FPS,
            codec="libx264",
            audio=False,
            threads=4,
            logger=None,
        )
    finally:
        if clip is not None:
            clip.close()

    return str(output_path)


def _resample_filter() -> int:
    if hasattr(Image, "Resampling"):
        return Image.Resampling.LANCZOS
    return Image.LANCZOS


def _save_transparent(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def _draw_customer_asset(path: Path, mood: str) -> None:
    image = Image.new("RGBA", (520, 720), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    skin = (255, 205, 164, 255)
    hair = (72, 45, 34, 255)
    shirt = {
        "neutral": (85, 196, 255, 255),
        "surprised": (255, 132, 161, 255),
        "thinking": (131, 236, 164, 255),
    }[mood]
    pants = (42, 50, 67, 255)
    outline = (24, 29, 39, 255)

    draw.ellipse((155, 55, 365, 265), fill=skin, outline=outline, width=8)
    draw.pieslice((140, 35, 380, 250), 180, 360, fill=hair)
    draw.rounded_rectangle((155, 285, 365, 520), radius=45, fill=shirt, outline=outline, width=8)
    draw.line((175, 330, 70, 470), fill=outline, width=28)
    draw.line((345, 330, 465, 440), fill=outline, width=28)
    draw.line((200, 520, 160, 680), fill=pants, width=36)
    draw.line((320, 520, 360, 680), fill=pants, width=36)

    if mood == "surprised":
        draw.ellipse((203, 138, 238, 178), fill=(255, 255, 255, 255), outline=outline, width=4)
        draw.ellipse((282, 138, 317, 178), fill=(255, 255, 255, 255), outline=outline, width=4)
        draw.ellipse((214, 150, 227, 166), fill=outline)
        draw.ellipse((293, 150, 306, 166), fill=outline)
        draw.ellipse((236, 200, 284, 245), fill=(94, 48, 58, 255))
    elif mood == "thinking":
        draw.arc((198, 148, 242, 178), 190, 350, fill=outline, width=5)
        draw.arc((280, 148, 324, 178), 190, 350, fill=outline, width=5)
        draw.arc((228, 205, 295, 245), 200, 340, fill=outline, width=6)
    else:
        draw.ellipse((210, 148, 230, 168), fill=outline)
        draw.ellipse((292, 148, 312, 168), fill=outline)
        draw.arc((225, 194, 300, 238), 20, 160, fill=outline, width=6)

    _save_transparent(image, path)


def _draw_cart_asset(path: Path) -> None:
    image = Image.new("RGBA", (430, 320), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    outline = (24, 29, 39, 255)
    metal = (117, 135, 161, 255)

    draw.line((70, 75, 125, 230), fill=outline, width=16)
    draw.rounded_rectangle((120, 90, 365, 220), radius=20, outline=outline, width=12, fill=(212, 231, 248, 210))
    for x in range(150, 350, 45):
        draw.line((x, 98, x - 20, 214), fill=metal, width=6)
    for y in (125, 165, 205):
        draw.line((132, y, 352, y), fill=metal, width=6)
    draw.line((350, 95, 395, 70), fill=outline, width=14)
    draw.ellipse((145, 238, 205, 298), fill=(35, 42, 56, 255))
    draw.ellipse((295, 238, 355, 298), fill=(35, 42, 56, 255))

    _save_transparent(image, path)


def _draw_product_asset(path: Path) -> None:
    image = Image.new("RGBA", (340, 430), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    outline = (24, 29, 39, 255)

    draw.rounded_rectangle((80, 80, 260, 350), radius=28, fill=(255, 190, 92, 255), outline=outline, width=8)
    draw.rectangle((80, 135, 260, 205), fill=(255, 132, 161, 255))
    draw.rounded_rectangle((105, 245, 235, 305), radius=16, fill=(245, 247, 250, 255), outline=outline, width=5)
    draw.rounded_rectangle((190, 40, 310, 120), radius=18, fill=(245, 247, 250, 245), outline=outline, width=6)
    draw.line((202, 118, 176, 170), fill=outline, width=6)

    _save_transparent(image, path)


def _draw_coin_asset(path: Path) -> None:
    image = Image.new("RGBA", (140, 140), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    draw.ellipse((12, 12, 128, 128), fill=(255, 207, 84, 255), outline=(142, 95, 31, 255), width=8)
    draw.ellipse((38, 38, 102, 102), outline=(255, 238, 161, 255), width=8)

    _save_transparent(image, path)


def _draw_brain_asset(path: Path) -> None:
    image = Image.new("RGBA", (260, 210), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    outline = (116, 57, 92, 255)
    pink = (255, 145, 195, 255)

    draw.ellipse((35, 62, 130, 150), fill=pink, outline=outline, width=6)
    draw.ellipse((95, 38, 185, 135), fill=pink, outline=outline, width=6)
    draw.ellipse((145, 78, 228, 160), fill=pink, outline=outline, width=6)
    draw.arc((62, 80, 126, 132), 190, 350, fill=outline, width=5)
    draw.arc((123, 70, 185, 120), 20, 170, fill=outline, width=5)
    draw.arc((150, 102, 212, 150), 180, 340, fill=outline, width=5)

    _save_transparent(image, path)


def _draw_store_background(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", VIDEO_SIZE, (246, 248, 252))
    draw = ImageDraw.Draw(image)

    draw.rectangle((0, 0, 1080, 260), fill=(212, 234, 255))
    draw.rectangle((0, 260, 1080, 1920), fill=(247, 241, 226))
    draw.polygon([(0, 1920), (1080, 1920), (820, 900), (260, 900)], fill=(237, 226, 206))
    draw.rectangle((0, 420, 250, 1320), fill=(117, 135, 161))
    draw.rectangle((830, 420, 1080, 1320), fill=(117, 135, 161))

    shelf_colors = [(255, 190, 92), (131, 236, 164), (85, 196, 255), (255, 132, 161)]
    for side_x in (20, 850):
        for row in range(5):
            y = 480 + row * 155
            draw.rounded_rectangle((side_x, y, side_x + 210, y + 98), radius=16, fill=(245, 247, 250))
            for item in range(3):
                x = side_x + 22 + item * 62
                draw.rounded_rectangle(
                    (x, y + 18, x + 42, y + 78),
                    radius=10,
                    fill=shelf_colors[(row + item) % len(shelf_colors)],
                )

    for y in range(1020, 1900, 170):
        draw.line((210, y, 870, y), fill=(222, 210, 190), width=4)

    image.save(path, quality=95)


def ensure_cartoon_assets(assets_root: str | Path) -> dict[str, Path]:
    root = Path(assets_root)
    paths = {
        "background": root / "backgrounds" / "store.png",
        "customer_neutral": root / "characters" / "customer_neutral.png",
        "customer_surprised": root / "characters" / "customer_surprised.png",
        "customer_thinking": root / "characters" / "customer_thinking.png",
        "cart": root / "props" / "cart.png",
        "product": root / "props" / "product.png",
        "coin": root / "props" / "coin.png",
        "brain": root / "props" / "brain.png",
    }

    if not paths["background"].exists():
        _draw_store_background(paths["background"])
    if not paths["customer_neutral"].exists():
        _draw_customer_asset(paths["customer_neutral"], "neutral")
    if not paths["customer_surprised"].exists():
        _draw_customer_asset(paths["customer_surprised"], "surprised")
    if not paths["customer_thinking"].exists():
        _draw_customer_asset(paths["customer_thinking"], "thinking")
    if not paths["cart"].exists():
        _draw_cart_asset(paths["cart"])
    if not paths["product"].exists():
        _draw_product_asset(paths["product"])
    if not paths["coin"].exists():
        _draw_coin_asset(paths["coin"])
    if not paths["brain"].exists():
        _draw_brain_asset(paths["brain"])

    return paths


def _ease_out(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return 1 - (1 - value) ** 3


def _bounce(t: float) -> float:
    return abs(math.sin(t * math.pi * 2.4)) * math.exp(-2.2 * t)


def _with_alpha(image: Image.Image, alpha: float) -> Image.Image:
    alpha = max(0.0, min(1.0, alpha))
    result = image.copy()
    if result.mode != "RGBA":
        result = result.convert("RGBA")
    channel = result.getchannel("A")
    channel = channel.point(lambda value: int(value * alpha))
    result.putalpha(channel)
    return result


def _asset(image_path: Path, size: tuple[int, int]) -> Image.Image:
    return Image.open(image_path).convert("RGBA").resize(size, _resample_filter())


def _choose_customer_asset(scene_prompt: str, assets: dict[str, Path]) -> Path:
    lowered = scene_prompt.lower()
    if any(word in lowered for word in ("surprised", "reacts", "discount", "shocked")):
        return assets["customer_surprised"]
    if any(word in lowered for word in ("think", "thinking", "pause", "calm", "brain", "psychology", "eyes")):
        return assets["customer_thinking"]
    return assets["customer_neutral"]


def _paste_rgba(base: Image.Image, overlay: Image.Image, xy: tuple[int, int]) -> None:
    base.alpha_composite(overlay, dest=xy)


def _zoom_frame(frame: Image.Image, zoom: float) -> Image.Image:
    if zoom <= 1.001:
        return frame

    width, height = frame.size
    crop_width = int(width / zoom)
    crop_height = int(height / zoom)
    left = (width - crop_width) // 2
    top = (height - crop_height) // 2
    cropped = frame.crop((left, top, left + crop_width, top + crop_height))
    return cropped.resize((width, height), _resample_filter())


def create_cartoon_scene_video(
    scene_prompt: str,
    duration: int,
    output_path: str | Path,
    assets_root: str | Path,
) -> str:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    assets = ensure_cartoon_assets(assets_root)

    render_size = (540, 960)
    scale = render_size[0] / VIDEO_SIZE[0]
    background = Image.open(assets["background"]).convert("RGBA").resize(render_size, _resample_filter())
    customer = _asset(_choose_customer_asset(scene_prompt, assets), (215, 298))
    cart = _asset(assets["cart"], (175, 130))
    product = _asset(assets["product"], (140, 178))
    coin = _asset(assets["coin"], (44, 44))
    brain = _asset(assets["brain"], (105, 85))

    lowered = scene_prompt.lower()
    show_brain = any(word in lowered for word in ("think", "brain", "psychology", "eyes", "calm", "pause"))
    show_many_coins = "coin" in lowered or "money" in lowered or "price" in lowered

    def make_frame(t: float) -> Any:
        import numpy as np

        progress = max(0.0, min(1.0, t / max(duration, 0.1)))
        eased = _ease_out(min(progress * 2.2, 1.0))
        frame = background.copy()

        customer_x = int((-390 + 500 * eased) * scale)
        customer_y = int((760 + int(math.sin(t * 3.2) * 7)) * scale)
        product_bounce = int(-34 * _bounce(min(progress * 2.3, 1.0)) * scale)
        product_x = int(650 * scale)
        product_y = int(790 * scale) + product_bounce
        cart_x = int((500 + int(20 * math.sin(t * 1.4))) * scale)
        cart_y = int(1270 * scale)

        _paste_rgba(frame, cart, (cart_x, cart_y))
        _paste_rgba(frame, product, (product_x, product_y))
        _paste_rgba(frame, customer, (customer_x, customer_y))

        coin_count = 4 if show_many_coins else 2
        for index in range(coin_count):
            coin_x = int((670 + index * 82 + int(math.sin(t * 2.0 + index) * 22)) * scale)
            fall = (progress * 900 + index * 140) % 900
            coin_y = int((230 + fall) * scale)
            _paste_rgba(frame, coin, (coin_x, coin_y))

        if show_brain or progress > 0.45:
            alpha = _ease_out((progress - 0.25) / 0.4)
            brain_y = int((520 + int(math.sin(t * 2.6) * 10)) * scale)
            _paste_rgba(frame, _with_alpha(brain, alpha), (int(650 * scale), brain_y))

        zoom = 1.0 + 0.045 * progress
        frame = _zoom_frame(frame, zoom).resize(VIDEO_SIZE, _resample_filter()).convert("RGB")
        return np.array(frame)

    clip = None
    try:
        clip = VideoClip(frame_function=make_frame, duration=float(duration))
        clip = _clip_with_fps(clip, CARTOON_FPS)
        clip.write_videofile(
            str(output),
            fps=CARTOON_FPS,
            codec="libx264",
            audio=False,
            threads=4,
            logger=None,
        )
    finally:
        if clip is not None:
            clip.close()

    return str(output)


def _create_subtitle_overlay(caption: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    image = Image.new("RGBA", VIDEO_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    box_left = 70
    box_right = VIDEO_SIZE[0] - 70
    box_top = 1180
    box_bottom = 1510
    max_text_width = box_right - box_left - 80
    max_text_height = box_bottom - box_top - 70

    font, lines, line_height = _fit_text(
        draw,
        caption,
        max_text_width,
        max_text_height,
        max_font_size=82,
        min_font_size=40,
    )

    draw.rounded_rectangle(
        (box_left, box_top, box_right, box_bottom),
        radius=28,
        fill=SUBTITLE_BOX,
        outline=(72, 82, 104, 230),
        width=2,
    )

    total_height = line_height * len(lines)
    y = box_top + ((box_bottom - box_top) - total_height) // 2

    for line in lines:
        width, _ = _text_size(draw, line, font)
        x = (VIDEO_SIZE[0] - width) // 2
        draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0, 190))
        draw.text((x, y), line, font=font, fill=TEXT_COLOR)
        y += line_height

    image.save(output_path)
    return output_path


def _draw_price_card(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    text: str,
    accent: tuple[int, int, int],
) -> None:
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle((x1, y1, x2, y2), radius=34, fill=(246, 248, 252, 245))
    draw.rounded_rectangle((x1, y1, x2, y2), radius=34, outline=accent, width=6)

    font = _load_font(86, bold=True)
    width, height = _text_size(draw, text, font)
    draw.text(
        (x1 + ((x2 - x1) - width) // 2, y1 + ((y2 - y1) - height) // 2 - 8),
        text,
        font=font,
        fill=(18, 23, 34, 255),
    )


def _draw_arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    color: tuple[int, int, int],
) -> None:
    draw.line((start, end), fill=(*color, 245), width=18)
    ex, ey = end
    draw.polygon(
        [(ex, ey), (ex - 46, ey - 30), (ex - 42, ey + 38)],
        fill=(*color, 245),
    )


def _create_controlled_overlay(scene: dict[str, Any], output_path: Path) -> Path | None:
    overlay_type = str(scene.get("overlay_type", "")).strip().lower()
    if not overlay_type:
        return None

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", VIDEO_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    accent = (255, 190, 92)

    if overlay_type == "price_comparison":
        _draw_price_card(draw, (104, 350, 500, 530), "999 ₽", (98, 213, 159))
        _draw_price_card(draw, (580, 350, 976, 530), "1000 ₽", (255, 132, 161))
        _draw_arrow(draw, (520, 438), (568, 438), accent)

    elif overlay_type == "price_999":
        _draw_price_card(draw, (300, 330, 780, 530), "999 ₽", (98, 213, 159))

    elif overlay_type == "price_1000":
        _draw_price_card(draw, (290, 330, 790, 530), "1000 ₽", (255, 132, 161))

    elif overlay_type == "arrow":
        _draw_arrow(draw, (260, 430), (820, 430), accent)

    elif overlay_type == "small_label":
        label = str(scene.get("overlay_label") or "Смотри на сумму").strip()
        font, lines, line_height = _fit_text(
            draw,
            label,
            max_width=760,
            max_height=120,
            max_font_size=44,
            min_font_size=32,
        )
        box_left = 170
        box_top = 350
        box_right = 910
        box_bottom = 500
        draw.rounded_rectangle(
            (box_left, box_top, box_right, box_bottom),
            radius=26,
            fill=(8, 10, 16, 225),
            outline=(*accent, 230),
            width=3,
        )
        total_height = len(lines) * line_height
        y = box_top + ((box_bottom - box_top) - total_height) // 2
        for line in lines:
            width, _ = _text_size(draw, line, font)
            draw.text(((VIDEO_SIZE[0] - width) // 2, y), line, font=font, fill=TEXT_COLOR)
            y += line_height

    else:
        return None

    image.save(output_path)
    return output_path


def concatenate_clips_with_subtitles(
    clip_paths: list[str | Path],
    scenes: list[dict[str, Any]],
    audio_path: str | Path,
    output_path: str | Path,
    temp_dir: str | Path,
) -> Path:
    """Concatenate provider clips, add Pillow subtitles, attach voice-over."""
    output_path = Path(output_path)
    temp_dir = Path(temp_dir)
    audio_path = Path(audio_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    scene_clips = []
    overlays = []
    audio = None
    base_clip = None
    final_clip = None

    try:
        if len(clip_paths) != len(scenes):
            raise ValueError("clip_paths and scenes must have the same length.")

        for clip_path, scene in zip(clip_paths, scenes):
            scene_clip = VideoFileClip(str(clip_path))
            scene_clip = _clip_with_duration(scene_clip, float(scene.get("duration", 4)))
            scene_clips.append(scene_clip)

        base_clip = concatenate_videoclips(scene_clips, method="compose")
        timeline = 0.0

        for index, scene in enumerate(scenes):
            caption = str(scene.get("caption") or scene.get("text") or "").strip()
            duration = float(scene.get("duration", 4))

            controlled_overlay_path = _create_controlled_overlay(
                scene,
                temp_dir / f"controlled_overlay_{index + 1:02d}.png",
            )
            if controlled_overlay_path is not None:
                try:
                    controlled_overlay = ImageClip(str(controlled_overlay_path), transparent=True)
                except TypeError:
                    controlled_overlay = ImageClip(str(controlled_overlay_path))

                controlled_overlay = _clip_with_start(controlled_overlay, timeline)
                controlled_overlay = _clip_with_duration(controlled_overlay, duration)
                controlled_overlay = _clip_with_position(controlled_overlay, ("center", "center"))
                overlays.append(controlled_overlay)

            if not caption:
                timeline += duration
                continue

            overlay_path = temp_dir / f"subtitle_{index + 1:02d}.png"
            _create_subtitle_overlay(caption, overlay_path)

            try:
                overlay = ImageClip(str(overlay_path), transparent=True)
            except TypeError:
                overlay = ImageClip(str(overlay_path))

            overlay = _clip_with_start(overlay, timeline)
            overlay = _clip_with_duration(overlay, duration)
            overlay = _clip_with_position(overlay, ("center", "center"))
            overlays.append(overlay)
            timeline += duration

        final_clip = CompositeVideoClip([base_clip, *overlays], size=VIDEO_SIZE)

        audio = AudioFileClip(str(audio_path))
        final_clip = _clip_with_audio(final_clip, audio)
        final_clip.write_videofile(
            str(output_path),
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            threads=4,
            logger=None,
        )

        return output_path
    finally:
        if final_clip is not None:
            final_clip.close()
        if base_clip is not None:
            base_clip.close()
        for overlay in overlays:
            overlay.close()
        for scene_clip in scene_clips:
            scene_clip.close()
        if audio is not None:
            audio.close()
