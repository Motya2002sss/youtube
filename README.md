# youtube_shorts_agent

Python-проект для автоматической сборки вертикального YouTube Shorts ролика в нише "деньги, покупки, маркетинг, психология покупок".

На первом этапе проект не публикует видео в YouTube. Он работает как агент-оркестратор: генерирует сценарий через OpenAI API, получает prompts для сцен, вызывает video provider, генерирует озвучку через бесплатный `edge-tts`, накладывает subtitles через Pillow + MoviePy и сохраняет результат локально.

## Установка

```bash
cd youtube_shorts_agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

На macOS/Linux активация окружения:

```bash
source .venv/bin/activate
```

## Настройка .env

Создайте файл `.env` на основе примера:

```bash
copy .env.example .env
```

На macOS/Linux:

```bash
cp .env.example .env
```

Откройте `.env` и вставьте ключ OpenAI:

```env
OPENAI_API_KEY=your_real_api_key_here
OPENAI_MODEL=gpt-4o-mini
VIDEO_PROVIDER=local_simple
RUNWAY_API_KEY=
LUMA_API_KEY=
```

`VIDEO_PROVIDER` сейчас поддерживает:

- `local_simple` - локальный fallback на Pillow/MoviePy.
- `stub_ai` - заглушка под будущие Runway/Luma: сохраняет prompt сцены в JSON и использует `local_simple` для клипа.

Реальные API Runway/Luma пока не подключены.

## Запуск

```bash
python main.py
```

Тестовая тема уже задана в `main.py`:

```text
Почему цена 999 кажется дешевле, чем 1000?
```

## Где будет результат

После успешного запуска файлы появятся в папке `outputs`:

- `outputs/short_001.mp4` - готовое вертикальное видео.
- `outputs/short_001.json` - title, description, script, voice_text, style_prompt, scenes, provider prompts и путь к видео.

Временные файлы озвучки, клипов сцен, subtitles и provider prompts сохраняются в `temp`.

## Pipeline

```text
topic
-> script JSON
-> style_prompt + scene_prompts
-> video provider generates scene clips
-> edge-tts generates voice-over
-> clips are concatenated
-> captions/subtitles are rendered by Pillow and composited over video
-> final mp4 + metadata JSON are saved to outputs
```

Важно: `scene_prompt` не должен просить AI-video модель рисовать текст, буквы, цифры, логотипы или субтитры. Текст для зрителя хранится в `caption` и добавляется самим Python поверх видео.

## Как устроен проект

- `main.py` - точка входа: тема, OpenAI, TTS, сборка видео, сохранение JSON.
- `prompts.py` - промпты для генерации сценария.
- `tts.py` - генерация MP3 через `edge-tts`.
- `video_provider.py` - интерфейс `VideoProvider`, `LocalSimpleProvider`, `StubAIProvider`.
- `video_generator.py` - локальная генерация fallback-клипов, склейка MP4 и наложение subtitles через Pillow/MoviePy.
- `assets/` - папка для будущих шрифтов, фоновых картинок, музыки.
- `outputs/` - готовые видео и метаданные.
- `temp/` - временные изображения сцен и аудио.

Код сделан так, чтобы позже было проще добавить источники тем из Google Sheets и автоматическую публикацию через YouTube API.
