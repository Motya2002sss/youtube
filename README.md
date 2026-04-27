# youtube_shorts_agent

Python-проект для автоматической сборки вертикального YouTube Shorts ролика в нише "деньги, покупки, маркетинг, психология покупок".

На первом этапе проект не публикует видео в YouTube. Он генерирует сценарий через OpenAI API, озвучку через бесплатный `edge-tts`, собирает вертикальное видео 1080x1920 через Pillow + MoviePy и сохраняет результат локально.

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
```

Опционально можно задать модель:

```env
OPENAI_MODEL=gpt-4o-mini
```

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
- `outputs/short_001.json` - title, description, script, voice_text, scenes и путь к видео.

Временные файлы озвучки и кадров сохраняются в `temp`.

## Как устроен проект

- `main.py` - точка входа: тема, OpenAI, TTS, сборка видео, сохранение JSON.
- `prompts.py` - промпты для генерации сценария.
- `tts.py` - генерация MP3 через `edge-tts`.
- `video_generator.py` - создание текстовых кадров через Pillow и сборка MP4 через MoviePy.
- `assets/` - папка для будущих шрифтов, фоновых картинок, музыки.
- `outputs/` - готовые видео и метаданные.
- `temp/` - временные изображения сцен и аудио.

Код сделан так, чтобы позже было проще добавить источники тем из Google Sheets и автоматическую публикацию через YouTube API.
