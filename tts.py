import asyncio
from pathlib import Path

import edge_tts


DEFAULT_VOICE = "ru-RU-DmitryNeural"


async def _generate_tts_async(
    text: str,
    output_path: Path,
    voice: str = DEFAULT_VOICE,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(str(output_path))
    return output_path


def generate_tts(
    text: str,
    output_path: str | Path,
    voice: str = DEFAULT_VOICE,
) -> Path:
    """Generate MP3 narration with edge-tts."""
    output_path = Path(output_path)

    if not text.strip():
        raise ValueError("TTS text is empty.")

    try:
        return asyncio.run(_generate_tts_async(text.strip(), output_path, voice))
    except RuntimeError as exc:
        # Keeps the CLI error readable if this function is later called from
        # an environment that already owns an event loop.
        raise RuntimeError(f"Failed to generate voice-over: {exc}") from exc
