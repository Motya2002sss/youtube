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
LUMA_API_BASE_URL=
```

`VIDEO_PROVIDER` сейчас поддерживает:

- `local_simple` - локальный fallback на Pillow/MoviePy.
- `stub_ai` - заглушка под будущие Runway/Luma: сохраняет prompt сцены в JSON и использует `local_simple` для клипа.
- `luma` - реальный provider для Luma Dream Machine API. Если provider падает, pipeline пишет `provider_error` в metadata и использует `local_simple` как fallback.

`local_simple` нужен только как fallback и для проверки pipeline. Для настоящего мультяшного результата нужен внешний AI-video provider, например Luma.

## Запуск local_simple

```env
VIDEO_PROVIDER=local_simple
```

```bash
python main.py
```

## Включение Luma

Добавьте ключ Luma в `.env`:

```env
VIDEO_PROVIDER=luma
LUMA_API_KEY=your_luma_api_key_here
LUMA_API_BASE_URL=https://api.lumalabs.ai/dream-machine/v1
```

`LUMA_API_BASE_URL` можно оставить пустым, тогда используется default URL из кода. Provider отправляет `scene_prompt` во внешний API, ждёт готовность генерации, скачивает mp4-клип сцены в `temp`, после чего общий pipeline склеивает клипы и накладывает subtitles/controlled overlays.

Если `LUMA_API_KEY` не задан, `LumaProvider` падает с понятной ошибкой. Если выбран `VIDEO_PROVIDER=luma`, верхний pipeline перехватывает ошибку, использует `local_simple` и записывает `provider_error` в JSON metadata.

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
-> controlled overlays and captions/subtitles are rendered by Pillow and composited over video
-> final mp4 + metadata JSON are saved to outputs
```

Важно: `scene_prompt` не должен просить AI-video модель рисовать текст, буквы, цифры, логотипы или субтитры. Текст для зрителя хранится в `caption`, а управляемые элементы вроде `999 ₽ vs 1000 ₽` задаются через `overlay_type` и добавляются самим Python поверх видео.

Пример сцены:

```json
{
  "caption": "999 выглядит почти выгодно",
  "scene_prompt": "a young shopper in a bright supermarket aisle looking surprised at a product with a blank price tag, colorful, vertical video, smooth camera movement, no text, no letters, no numbers, no subtitles, no logos",
  "duration": 4,
  "overlay_type": "price_comparison"
}
```

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
