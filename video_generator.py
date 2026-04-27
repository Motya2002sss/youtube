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
        VideoFileClip,
        concatenate_videoclips,
        vfx,
    )
except ImportError:  # MoviePy 1.x
    from moviepy.editor import (
        AudioFileClip,
        CompositeVideoClip,
        ImageClip,
        VideoFileClip,
        concatenate_videoclips,
        vfx,
    )


VIDEO_SIZE = (1080, 1920)
FPS = 30
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
