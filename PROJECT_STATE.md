# Project State

Repo: YouTube Shorts agent.

Current working state:
- Python project runs locally.
- main.py generates one Shorts video.
- OpenAI generates script JSON.
- edge-tts generates voice.
- video_provider supports:
  - local_simple
  - cartoon_assets
  - stub_ai
  - luma skeleton
- cartoon_assets creates local 2D cartoon scenes from generated Pillow assets.
- final mp4 is saved to outputs/short_001.mp4.
- metadata is saved to outputs/short_001.json.

Current priority:
Improve cartoon visual quality before adding external AI-video providers or YouTube upload.
Next major step is to connect an external AI-video provider or replace primitive assets with better-looking cartoon assets.

Do not add:
- YouTube API yet
- Google Sheets yet
- automatic publishing yet

Next tasks:
1. Improve cartoon_assets visual quality.
2. Add better scene variety.
3. Add nicer character poses.
4. Add background music later.
5. Only after visuals are good, add Luma/Runway provider.
