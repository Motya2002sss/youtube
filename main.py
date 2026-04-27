from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from prompts import SYSTEM_PROMPT, build_user_prompt
from tts import DEFAULT_VOICE, generate_tts
from video_generator import concatenate_clips_with_subtitles
from video_provider import get_video_provider


PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "outputs"
TEMP_DIR = PROJECT_DIR / "temp"

TOPIC = "Почему цена 999 кажется дешевле, чем 1000?"
OUTPUT_STEM = "short_001"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_VIDEO_PROVIDER = "local_simple"
DEFAULT_STYLE_PROMPT = (
    "3D cartoon style, colorful commercial video, vertical 9:16, smooth camera movement, "
    "bright retail and money psychology visuals, consistent characters and lighting"
)
NO_TEXT_PROMPT = "no text, no letters, no numbers, no subtitles, no logos"
FALLBACK_SCRIPT = {
    "title": "Почему 999 кажется дешевле?",
    "description": "Коротко о том, почему цена 999 воспринимается легче, чем 1000.",
    "style_prompt": DEFAULT_STYLE_PROMPT,
    "voice_text": (
        "Почему девятьсот девяносто девять кажется дешевле, чем тысяча? "
        "Мозг читает цену слева направо. Первая цифра девять, а не десять, "
        "и покупка уже ощущается легче. Разница всего один рубль, но ощущение "
        "другое. Например, тысяча звучит как круглая сумма. А девятьсот "
        "девяносто девять выглядит как что-то меньшее и почти выгодное. "
        "Так работает простая ценовая рамка. Важно помнить: смотри не на "
        "первую цифру, а на реальную сумму. Минус один рубль не всегда значит "
        "выгодная покупка."
    ),
    "scenes": [
        {
            "caption": "Почему 999 кажется дешевле?",
            "scene_prompt": (
                "A young shopper in a bright supermarket aisle looks surprised at a blank "
                f"price tag, colorful, vertical video, smooth camera movement, {NO_TEXT_PROMPT}"
            ),
            "duration": 4,
        },
        {
            "caption": "Мозг читает цену слева",
            "scene_prompt": (
                "A close-up of eyes scanning a product shelf from left to right, retail "
                f"psychology mood, vertical video, smooth camera movement, {NO_TEXT_PROMPT}"
            ),
            "duration": 4,
        },
        {
            "caption": "Первая цифра решает ощущение",
            "scene_prompt": (
                "A shopper compares two similar products with blank labels and reacts "
                f"emotionally, colorful store background, vertical video, {NO_TEXT_PROMPT}"
            ),
            "duration": 5,
        },
        {
            "caption": "1000 звучит как крупная сумма",
            "scene_prompt": (
                "A large abstract coin stack feels heavy and serious beside a shopping "
                f"basket, vertical video, smooth camera movement, {NO_TEXT_PROMPT}"
            ),
            "duration": 5,
        },
        {
            "caption": "999 выглядит почти выгодно",
            "scene_prompt": (
                "A shopper smiles at a product with a blank discount-style tag, bright "
                f"supermarket aisle, vertical video, smooth camera movement, {NO_TEXT_PROMPT}"
            ),
            "duration": 5,
        },
        {
            "caption": "Разница всего один рубль",
            "scene_prompt": (
                "Two nearly identical products sit side by side while a small coin falls "
                f"between them, vertical video, smooth camera movement, {NO_TEXT_PROMPT}"
            ),
            "duration": 4,
        },
        {
            "caption": "Смотри на реальную сумму",
            "scene_prompt": (
                "A shopper pauses, thinks, and checks a shopping basket calmly before buying, "
                f"colorful retail scene, vertical video, smooth camera movement, {NO_TEXT_PROMPT}"
            ),
            "duration": 5,
        },
    ],
}


def extract_json_object(raw_text: str) -> dict[str, Any]:
    """Extract the first valid JSON object from a model response."""
    cleaned = raw_text.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for index, char in enumerate(cleaned):
        if char != "{":
            continue

        try:
            parsed, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue

        if isinstance(parsed, dict):
            return parsed

    raise ValueError("OpenAI response does not contain a valid JSON object.")


def _safe_text(value: Any, fallback: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback


def _safe_duration(value: Any, default: int = 4) -> int:
    try:
        duration = int(float(value))
    except (TypeError, ValueError):
        return default
    return max(3, min(6, duration))


def _ensure_no_text_prompt(scene_prompt: str) -> str:
    lowered = scene_prompt.lower()
    required_parts = ["no text", "no letters", "no numbers", "no subtitles", "no logos"]
    missing_parts = [part for part in required_parts if part not in lowered]

    if not missing_parts:
        return scene_prompt

    return f"{scene_prompt.rstrip(' .')}, {', '.join(missing_parts)}"


def build_provider_scene_prompt(style_prompt: str, scene_prompt: str) -> str:
    return _ensure_no_text_prompt(f"{style_prompt.rstrip(' .')}. {scene_prompt.strip()}")


def normalize_script_payload(payload: dict[str, Any]) -> dict[str, Any]:
    title = _safe_text(payload.get("title"), "Shorts о психологии покупок")
    description = _safe_text(
        payload.get("description"),
        "Короткое объяснение приема из маркетинга и психологии покупок.",
    )
    voice_text = _safe_text(payload.get("voice_text"), "")
    style_prompt = _safe_text(payload.get("style_prompt"), DEFAULT_STYLE_PROMPT)

    raw_scenes = payload.get("scenes")
    if not isinstance(raw_scenes, list):
        raise ValueError("OpenAI JSON must contain a scenes list.")

    scenes: list[dict[str, Any]] = []
    for scene in raw_scenes:
        if not isinstance(scene, dict):
            continue

        caption = _safe_text(scene.get("caption") or scene.get("text"), "")
        if not caption:
            continue

        scene_prompt = _safe_text(
            scene.get("scene_prompt"),
            (
                "A visual metaphor for shopping psychology in a bright retail environment, "
                f"vertical video, smooth camera movement, {NO_TEXT_PROMPT}"
            ),
        )

        scenes.append(
            {
                "caption": caption,
                "scene_prompt": _ensure_no_text_prompt(scene_prompt),
                "duration": _safe_duration(scene.get("duration", 4)),
            }
        )

    if not scenes:
        raise ValueError("OpenAI JSON does not contain valid scenes.")

    if not voice_text:
        voice_text = " ".join(scene["caption"] for scene in scenes)

    return {
        "title": title,
        "description": description,
        "voice_text": voice_text,
        "style_prompt": style_prompt,
        "scenes": scenes,
    }


def generate_script(topic: str) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Create .env from .env.example and add your API key."
        )

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(topic)},
            ],
            temperature=0.8,
            response_format={"type": "json_object"},
        )
    except Exception as exc:
        raise RuntimeError(f"OpenAI request failed: {exc}") from exc

    content = response.choices[0].message.content
    if not content:
        raise ValueError("OpenAI returned an empty response.")

    payload = extract_json_object(content)
    return normalize_script_payload(payload)


def save_metadata(metadata: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    load_dotenv(PROJECT_DIR / ".env")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    video_path = OUTPUT_DIR / f"{OUTPUT_STEM}.mp4"
    metadata_path = OUTPUT_DIR / f"{OUTPUT_STEM}.json"
    audio_path = TEMP_DIR / f"{OUTPUT_STEM}.mp3"
    provider_name = os.getenv("VIDEO_PROVIDER", DEFAULT_VIDEO_PROVIDER)

    try:
        print(f"Topic: {TOPIC}")
        print("Generating script with OpenAI...")
        generation_source = "openai"
        try:
            script_payload = generate_script(TOPIC)
        except Exception as exc:
            if os.getenv("ALLOW_LOCAL_FALLBACK") != "1":
                raise

            print(f"OpenAI failed, using local fallback script: {exc}")
            script_payload = normalize_script_payload(dict(FALLBACK_SCRIPT))
            generation_source = "local_fallback"

        print(f"Generating scene clips with provider: {provider_name}")
        provider = get_video_provider(provider_name, TEMP_DIR)
        scene_clip_paths: list[str] = []

        for index, scene in enumerate(script_payload["scenes"], start=1):
            scene_clip_path = TEMP_DIR / f"{OUTPUT_STEM}_scene_{index:02d}.mp4"
            provider_prompt = build_provider_scene_prompt(
                script_payload["style_prompt"],
                scene["scene_prompt"],
            )
            scene_clip_paths.append(
                provider.generate_scene_video(
                    scene_prompt=provider_prompt,
                    duration=scene["duration"],
                    output_path=str(scene_clip_path),
                )
            )
            scene["provider_prompt"] = provider_prompt
            scene["clip_path"] = str(scene_clip_path)

        print(f"Generating voice-over with {DEFAULT_VOICE}...")
        generate_tts(script_payload["voice_text"], audio_path, voice=DEFAULT_VOICE)

        print("Concatenating clips and adding subtitles...")
        concatenate_clips_with_subtitles(
            clip_paths=scene_clip_paths,
            scenes=script_payload["scenes"],
            audio_path=audio_path,
            output_path=video_path,
            temp_dir=TEMP_DIR,
        )

        metadata = {
            "topic": TOPIC,
            "generation_source": generation_source,
            "video_provider": provider_name,
            "video_path": str(video_path),
            "script": script_payload["voice_text"],
            **script_payload,
        }
        save_metadata(metadata, metadata_path)

        print(f"Done: {video_path}")
        print(f"Metadata: {metadata_path}")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
