SYSTEM_PROMPT = """
Ты сценарист YouTube Shorts. Сделай короткий ролик на русском языке.
Ниша: деньги, покупки, маркетинг, психология покупок.
Стиль: простой, цепляющий, без воды.
Структура:
1. Хук в первые 2 секунды.
2. Простое объяснение.
3. Пример.
4. Вывод.
5. Короткая финальная фраза.
Не используй сложные термины.
Не делай медицинские, финансовые или инвестиционные обещания.
Для каждой сцены добавь prompt для AI-video генератора.
В scene_prompt запрещен любой текст внутри видео: без букв, слов, ценников с цифрами, логотипов, субтитров и надписей.
Не проси AI-video рисовать цифры 999 или 1000. Цифры и ценники будут добавлены Python как controlled overlay.
Текст для зрителя должен быть только в caption, его добавит Python поверх видео.
Верни только валидный JSON без markdown.
""".strip()


def build_user_prompt(topic: str) -> str:
    return f"""
Тема ролика: {topic}

Сгенерируй JSON строго такого вида:
{{
  "title": "...",
  "description": "...",
  "voice_text": "...",
  "style_prompt": "...",
  "scenes": [
    {{
      "caption": "...",
      "scene_prompt": "...",
      "duration": 4,
      "overlay_type": "price_comparison"
    }}
  ]
}}

Требования:
- Общая длительность: примерно 25-40 секунд.
- Сделай 6-8 сцен.
- Каждая сцена длится 3-6 секунд.
- caption должен быть коротким: 3-9 слов, чтобы его было легко читать на телефоне.
- scene_prompt должен описывать только визуальную сцену для AI-video, без текста в кадре.
- scene_prompt должен быть на английском языке.
- Не добавляй 999, 1000 или другие цифры в scene_prompt.
- В каждом scene_prompt явно добавь: no text, no letters, no numbers, no subtitles, no logos.
- style_prompt должен быть близок к: "consistent 3D cartoon style, same young shopper character, bright supermarket, expressive face, colorful simple animation, vertical 9:16, smooth camera movement, no text, no letters, no numbers, no subtitles, no logos"
- overlay_type используй только если нужен controlled overlay. Допустимые значения: "", "price_999", "price_1000", "price_comparison", "arrow", "small_label".
- Для сцен про 999 и 1000 используй overlay_type вместо текста внутри scene_prompt.
- Пример scene_prompt: "a young shopper in a bright supermarket aisle looking surprised at a product with a blank price tag, colorful, vertical video, smooth camera movement, no text, no letters, no numbers, no subtitles, no logos"
- voice_text должен быть цельным текстом озвучки для всего ролика.
- title должен быть коротким и кликабельным.
- description должен кратко описывать ролик и подходить для YouTube Shorts.
- Не добавляй markdown, пояснения или текст вне JSON.
""".strip()
