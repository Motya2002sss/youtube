from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path

from video_generator import create_local_scene_video


class VideoProvider(ABC):
    @abstractmethod
    def generate_scene_video(self, scene_prompt: str, duration: int, output_path: str) -> str:
        """Generate a vertical video clip for one scene and return its path."""


class LocalSimpleProvider(VideoProvider):
    """Fallback provider that creates a simple local video clip with Pillow/MoviePy."""

    def generate_scene_video(self, scene_prompt: str, duration: int, output_path: str) -> str:
        return create_local_scene_video(
            scene_prompt=scene_prompt,
            duration=duration,
            output_path=output_path,
        )


class StubAIProvider(VideoProvider):
    """
    Placeholder for future AI-video providers.

    It stores the prompt that would be sent to Runway/Luma/etc. and delegates
    actual clip creation to LocalSimpleProvider so the pipeline remains runnable.
    """

    def __init__(self, prompt_log_dir: str | Path):
        self.prompt_log_dir = Path(prompt_log_dir)
        self.local_provider = LocalSimpleProvider()

    def generate_scene_video(self, scene_prompt: str, duration: int, output_path: str) -> str:
        output = Path(output_path)
        self.prompt_log_dir.mkdir(parents=True, exist_ok=True)

        prompt_log_path = self.prompt_log_dir / f"{output.stem}_prompt.json"
        prompt_log_path.write_text(
            json.dumps(
                {
                    "provider": "stub_ai",
                    "scene_prompt": scene_prompt,
                    "duration": duration,
                    "output_path": str(output),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        return self.local_provider.generate_scene_video(scene_prompt, duration, output_path)


def get_video_provider(provider_name: str, temp_dir: str | Path) -> VideoProvider:
    normalized = provider_name.strip().lower()

    if normalized == "local_simple":
        return LocalSimpleProvider()

    if normalized in {"stub_ai", "stub"}:
        return StubAIProvider(prompt_log_dir=Path(temp_dir) / "provider_prompts")

    raise ValueError(
        f"Unknown VIDEO_PROVIDER={provider_name!r}. "
        "Supported providers: local_simple, stub_ai."
    )
