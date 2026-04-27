from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from video_generator import create_cartoon_scene_video, create_local_scene_video


DEFAULT_LUMA_API_BASE_URL = "https://api.lumalabs.ai/dream-machine/v1"
DEFAULT_LUMA_MODEL = "ray-flash-2"
DEFAULT_LUMA_RESOLUTION = "720p"
DEFAULT_LUMA_POLL_INTERVAL = 10
DEFAULT_LUMA_TIMEOUT = 900


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


class CartoonAssetsProvider(VideoProvider):
    """Local 2D cartoon provider based on generated Pillow assets."""

    def __init__(self, assets_root: str | Path):
        self.assets_root = Path(assets_root)

    def generate_scene_video(self, scene_prompt: str, duration: int, output_path: str) -> str:
        return create_cartoon_scene_video(
            scene_prompt=scene_prompt,
            duration=duration,
            output_path=output_path,
            assets_root=self.assets_root,
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


class LumaProvider(VideoProvider):
    """Luma Dream Machine text-to-video provider."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = DEFAULT_LUMA_MODEL,
        resolution: str = DEFAULT_LUMA_RESOLUTION,
        poll_interval: int = DEFAULT_LUMA_POLL_INTERVAL,
        timeout: int = DEFAULT_LUMA_TIMEOUT,
    ):
        self.api_key = (api_key or os.getenv("LUMA_API_KEY") or "").strip()
        if not self.api_key:
            raise RuntimeError("LUMA_API_KEY is not set. Add it to .env or use VIDEO_PROVIDER=local_simple.")

        self.base_url = (base_url or os.getenv("LUMA_API_BASE_URL") or DEFAULT_LUMA_API_BASE_URL).rstrip("/")
        self.model = model
        self.resolution = resolution
        self.poll_interval = poll_interval
        self.timeout = timeout

    def generate_scene_video(self, scene_prompt: str, duration: int, output_path: str) -> str:
        generation = self.create_generation(scene_prompt=scene_prompt, duration=duration)
        completed_generation = self.poll_generation(str(generation["id"]))
        return self.download_video(completed_generation, output_path)

    def create_generation(self, scene_prompt: str, duration: int) -> dict[str, Any]:
        """Create a Luma generation and return the response JSON.

        Official docs expose Dream Machine generation creation under the
        generations API. Keep this method isolated so endpoint changes do not
        leak into the rest of the pipeline.
        """
        payload = {
            "prompt": scene_prompt,
            "model": self.model,
            "aspect_ratio": "9:16",
            "resolution": self.resolution,
            "duration": self._luma_duration(duration),
        }
        return self._request_json("POST", "/generations/video", payload)

    def poll_generation(self, generation_id: str) -> dict[str, Any]:
        """Poll Luma until generation is completed or failed."""
        deadline = time.monotonic() + self.timeout

        while time.monotonic() < deadline:
            generation = self._request_json("GET", f"/generations/{generation_id}")
            state = str(generation.get("state", "")).lower()

            if state == "completed":
                return generation

            if state in {"failed", "rejected"}:
                reason = generation.get("failure_reason") or generation.get("error") or "unknown reason"
                raise RuntimeError(f"Luma generation failed: {reason}")

            time.sleep(self.poll_interval)

        raise TimeoutError(f"Luma generation timed out after {self.timeout} seconds: {generation_id}")

    def download_video(self, generation: dict[str, Any], output_path: str) -> str:
        """Download the completed Luma video asset to output_path."""
        assets = generation.get("assets")
        if not isinstance(assets, dict):
            raise RuntimeError("Luma response does not contain assets.")

        video_url = assets.get("video")
        if not isinstance(video_url, str) or not video_url:
            raise RuntimeError("Luma response does not contain assets.video.")

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        request = urllib.request.Request(video_url, headers={"User-Agent": "youtube-shorts-agent/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                output.write_bytes(response.read())
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Failed to download Luma video: {exc}") from exc

        return str(output)

    def _request_json(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = None
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(
            url=f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Luma API HTTP {exc.code}: {error_body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Luma API request failed: {exc}") from exc

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Luma API returned invalid JSON: {raw[:300]}") from exc

        if not isinstance(parsed, dict):
            raise RuntimeError("Luma API returned a non-object JSON response.")

        return parsed

    @staticmethod
    def _luma_duration(duration: int) -> str:
        # Luma duration is a string enum. Map short Shorts scenes to the
        # closest practical generation length and trim in MoviePy later.
        return "5s" if duration <= 5 else "9s"


def get_video_provider(provider_name: str, temp_dir: str | Path) -> VideoProvider:
    normalized = provider_name.strip().lower()

    if normalized == "local_simple":
        return LocalSimpleProvider()

    if normalized == "cartoon_assets":
        return CartoonAssetsProvider(assets_root=Path(temp_dir).parent / "assets" / "generated")

    if normalized in {"stub_ai", "stub"}:
        return StubAIProvider(prompt_log_dir=Path(temp_dir) / "provider_prompts")

    if normalized == "luma":
        return LumaProvider()

    raise ValueError(
        f"Unknown VIDEO_PROVIDER={provider_name!r}. "
        "Supported providers: local_simple, cartoon_assets, stub_ai, luma."
    )
