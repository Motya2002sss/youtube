from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import fal_client


PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "outputs"
OUTPUT_PATH = OUTPUT_DIR / "fal_test.mp4"

FAL_ENDPOINT = "fal-ai/pika/v2.1/text-to-video"
PRICING_API_URL = "https://api.fal.ai/v1/models/pricing"


def main() -> int:
    load_dotenv(PROJECT_DIR / ".env")

    fal_key = (os.getenv("FAL_KEY") or "").strip()
    if not fal_key:
        print("FAL_KEY не найден. Добавьте FAL_KEY в .env и повторите smoke test.", file=sys.stderr)
        return 2

    print(f"Fal endpoint: {FAL_ENDPOINT}")
    print("Checking Fal pricing/access before generation...")

    try:
        pricing = fetch_pricing(fal_key)
    except Exception as exc:
        print(format_fal_error("Fal pricing/access check failed", exc), file=sys.stderr)
        return 2

    prices = pricing.get("prices") if isinstance(pricing, dict) else None
    if isinstance(prices, list) and prices:
        for price in prices:
            endpoint_id = price.get("endpoint_id", FAL_ENDPOINT)
            unit_price = price.get("unit_price", "unknown")
            currency = price.get("currency", "USD")
            unit = price.get("unit", "unit")
            print(f"Pricing OK: {endpoint_id} costs {unit_price} {currency}/{unit}")
    else:
        print("Pricing API answered, but did not return a price row for this endpoint.")
        print("Continuing with exactly one 5-second Pika test generation.")

    print("Starting one short Pika text-to-video test generation...")

    try:
        result = fal_client.subscribe(
            FAL_ENDPOINT,
            arguments={
                "prompt": (
                    "A simple colorful cartoon coin gently spinning on a clean light background, "
                    "vertical short video, smooth motion, no text, no letters, no logos"
                ),
                "aspect_ratio": "9:16",
                "resolution": "720p",
                "duration": 5,
                "negative_prompt": "text, letters, numbers, logo, watermark",
            },
            with_logs=True,
            on_queue_update=print_queue_update,
            start_timeout=300,
            client_timeout=900,
        )
    except Exception as exc:
        print(format_fal_error("Fal/Pika generation failed", exc), file=sys.stderr)
        return 3

    try:
        video_url = extract_video_url(result)
        download_file(video_url, OUTPUT_PATH)
    except Exception as exc:
        print(format_fal_error("Fal generation succeeded, but downloading the mp4 failed", exc), file=sys.stderr)
        return 4

    print(f"Success: saved {OUTPUT_PATH}")
    return 0


def fetch_pricing(fal_key: str) -> dict[str, Any]:
    query = urllib.parse.urlencode({"endpoint_id": FAL_ENDPOINT})
    request = urllib.request.Request(
        f"{PRICING_API_URL}?{query}",
        headers={
            "Accept": "application/json",
            "Authorization": f"Key {fal_key}",
            "User-Agent": "youtube-shorts-agent/1.0",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Fal pricing API HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Fal pricing API request failed: {exc}") from exc

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Fal pricing API returned invalid JSON: {raw[:300]}") from exc

    if not isinstance(parsed, dict):
        raise RuntimeError("Fal pricing API returned a non-object JSON response.")

    return parsed


def print_queue_update(status: Any) -> None:
    state = getattr(status, "status", None) or status.__class__.__name__
    print(f"Fal queue status: {state}")

    logs = getattr(status, "logs", None)
    if isinstance(logs, list):
        for log in logs[-3:]:
            message = getattr(log, "message", None)
            if message:
                print(f"Fal log: {message}")


def extract_video_url(result: Any) -> str:
    payload = result
    if isinstance(result, dict) and isinstance(result.get("data"), dict):
        payload = result["data"]

    if not isinstance(payload, dict):
        raise RuntimeError(f"Unexpected Fal response type: {type(payload).__name__}")

    video = payload.get("video")
    if isinstance(video, dict) and isinstance(video.get("url"), str):
        return video["url"]

    raise RuntimeError(f"Fal response does not contain video.url: {json.dumps(payload, ensure_ascii=False)[:500]}")


def download_file(url: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "youtube-shorts-agent/1.0"})

    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            output_path.write_bytes(response.read())
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to download video: {exc}") from exc


def format_fal_error(prefix: str, exc: Exception) -> str:
    text = str(exc)
    lowered = text.lower()

    if any(marker in lowered for marker in ("unauthorized", "forbidden", "invalid api key", "401", "403", "auth")):
        hint = "Проверьте FAL_KEY: ключ не принят Fal.ai или у него нет доступа."
    elif any(marker in lowered for marker in ("credit", "credits", "billing", "payment", "balance", "insufficient", "402")):
        hint = "Fal.ai сообщает о billing/credits: пополните баланс или включите billing в аккаунте."
    else:
        hint = "Проверьте доступность endpoint, сеть и ответ Fal.ai выше."

    return f"{prefix}: {text}\n{hint}"


if __name__ == "__main__":
    raise SystemExit(main())
