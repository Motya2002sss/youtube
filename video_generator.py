from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

try:
    from moviepy import AudioFileClip, ImageClip, concatenate_videoclips, vfx
except ImportError:  # MoviePy 1.x
    from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips, vfx


VIDEO_SIZE = (1080, 1920)
FPS = 30
BACKGROUND = (12, 15, 22)
TEXT_COLOR = (245, 247, 250)
MUTED_TEXT = (155, 164, 178)
ACCENT_COLORS = [
    (85, 196, 255),
    (255, 190, 92),
    (131, 236, 164),
    (255, 132, 161),
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
    max_font_size: int = 96,
    min_font_size: int = 52,
) -> tuple[ImageFont.ImageFont, list[str], int]:
    for font_size in range(max_font_size, min_font_size - 1, -2):
        font = _load_font(font_size, bold=True)
        lines = _wrap_text(draw, text, font, max_width)
        line_height = math.ceil(font_size * 1.2)
        total_height = line_height * len(lines)
        widest = max(_text_size(draw, line, font)[0] for line in lines)

        if widest <= max_width and total_height <= max_height:
            return font, lines, line_height

    font = _load_font(min_font_size, bold=True)
    lines = _wrap_text(draw, text, font, max_width)
    return font, lines, math.ceil(min_font_size * 1.2)


def _draw_background(draw: ImageDraw.ImageDraw, scene_index: int) -> None:
    width, height = VIDEO_SIZE
    accent = ACCENT_COLORS[scene_index % len(ACCENT_COLORS)]

    draw.rectangle((0, 0, width, height), fill=BACKGROUND)
    draw.rectangle((0, 0, width, 20), fill=accent)
    draw.rounded_rectangle((70, 1650, 1010, 1662), radius=6, fill=(34, 39, 51))
    draw.rounded_rectangle((70, 1650, 70 + 160 + scene_index * 18, 1662), radius=6, fill=accent)

    # A very subtle visual anchor so the frame does not look empty.
    draw.ellipse((760, 90, 1280, 610), outline=(28, 34, 48), width=6)
    draw.ellipse((-230, 1270, 270, 1770), outline=(28, 34, 48), width=6)


def create_scene_image(
    text: str,
    image_path: Path,
    scene_index: int,
    total_scenes: int,
) -> Path:
    image_path.parent.mkdir(parents=True, exist_ok=True)

    image = Image.new("RGB", VIDEO_SIZE, BACKGROUND)
    draw = ImageDraw.Draw(image)
    _draw_background(draw, scene_index)

    max_text_width = 900
    max_text_height = 940
    font, lines, line_height = _fit_text(draw, text, max_text_width, max_text_height)

    total_height = line_height * len(lines)
    y = (VIDEO_SIZE[1] - total_height) // 2 - 40

    for line in lines:
        width, _ = _text_size(draw, line, font)
        x = (VIDEO_SIZE[0] - width) // 2
        draw.text((x + 4, y + 4), line, font=font, fill=(0, 0, 0))
        draw.text((x, y), line, font=font, fill=TEXT_COLOR)
        y += line_height

    small_font = _load_font(34, bold=False)
    footer = f"{scene_index + 1}/{total_scenes}"
    draw.text((70, 1700), footer, font=small_font, fill=MUTED_TEXT)

    image.save(image_path, quality=95)
    return image_path


def _with_duration(clip: ImageClip, duration: float) -> ImageClip:
    if hasattr(clip, "with_duration"):
        return clip.with_duration(duration)
    return clip.set_duration(duration)


def _with_fps(clip: ImageClip, fps: int) -> ImageClip:
    if hasattr(clip, "with_fps"):
        return clip.with_fps(fps)
    return clip.set_fps(fps)


def _with_audio(clip, audio):
    if hasattr(clip, "with_audio"):
        return clip.with_audio(audio)
    return clip.set_audio(audio)


def _apply_fades(clip: ImageClip, fade_duration: float = 0.25) -> ImageClip:
    try:
        if hasattr(clip, "with_effects") and hasattr(vfx, "FadeIn"):
            return clip.with_effects([vfx.FadeIn(fade_duration), vfx.FadeOut(fade_duration)])

        if hasattr(clip, "fx") and hasattr(vfx, "fadein") and hasattr(vfx, "fadeout"):
            return clip.fx(vfx.fadein, fade_duration).fx(vfx.fadeout, fade_duration)
    except Exception:
        return clip

    return clip


def _safe_duration(value: object, default: int = 4) -> int:
    try:
        duration = int(float(value))
    except (TypeError, ValueError):
        return default
    return max(3, min(6, duration))


def _normalize_scenes(scenes: Iterable[dict]) -> list[dict]:
    normalized: list[dict] = []

    for scene in scenes:
        if not isinstance(scene, dict):
            continue

        text = str(scene.get("text", "")).strip()
        if not text:
            continue

        normalized.append(
            {
                "text": text,
                "duration": _safe_duration(scene.get("duration", 4)),
            }
        )

    if not normalized:
        raise ValueError("No valid scenes for video generation.")

    return normalized


def build_video(
    scenes: list[dict],
    audio_path: str | Path,
    output_path: str | Path,
    temp_dir: str | Path,
) -> Path:
    """Build a vertical Shorts video from Pillow-generated scene images."""
    audio_path = Path(audio_path)
    output_path = Path(output_path)
    temp_dir = Path(temp_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    normalized_scenes = _normalize_scenes(scenes)
    clips = []
    audio = None
    final_clip = None

    try:
        audio = AudioFileClip(str(audio_path))
        scene_duration = sum(scene["duration"] for scene in normalized_scenes)

        if audio.duration and audio.duration > scene_duration:
            extra_time = min(8, audio.duration - scene_duration + 0.3)
            normalized_scenes[-1]["duration"] += extra_time

        total_scenes = len(normalized_scenes)

        for index, scene in enumerate(normalized_scenes):
            image_path = temp_dir / f"scene_{index + 1:02d}.png"
            create_scene_image(scene["text"], image_path, index, total_scenes)

            clip = ImageClip(str(image_path))
            clip = _with_duration(clip, float(scene["duration"]))
            clip = _with_fps(clip, FPS)
            clip = _apply_fades(clip)
            clips.append(clip)

        final_clip = concatenate_videoclips(clips, method="compose")
        final_clip = _with_audio(final_clip, audio)

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
        for clip in clips:
            clip.close()
        if audio is not None:
            audio.close()
