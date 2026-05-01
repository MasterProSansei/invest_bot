# Smart Investment Mentor Telegram Bot

Telegram-бот для образовательного разбора инвестиционных идей простым языком.

## 1. Настройки

Все секреты хранятся только в файле `.env`. Не присылай токены и API-ключи в чат.

Файл `.env` должен выглядеть так:

```env
TELEGRAM_BOT_TOKEN=токен_от_BotFather
GEMINI_API_KEY=ключ_от_Google_AI_Studio
GEMINI_MODEL=gemini-2.5-flash
```

Google Gemini API key создается здесь:

https://aistudio.google.com/apikey

## 2. Установка

В терминале VS Code, находясь в папке проекта:

```powershell
py -m pip install -r requirements.txt
```

## 3. Запуск

```powershell
py bot.py
```

Если увидишь:

```text
Smart Investment Mentor bot is running with Gemini. Press Ctrl+C to stop.
```

Открой бота в Telegram и напиши `/start`.

## 4. Остановка

В терминале нажми:

```text
Ctrl+C
```

Пока терминал открыт, бот работает. Если закрыть терминал или выключить компьютер, бот остановится.

## 5. Защита лимитов

Чтобы беречь бесплатный лимит Gemini, бот:

- принимает 1 запрос от пользователя раз в 10 секунд;
- не принимает слишком длинные сообщения;
- просит Gemini отвечать кратко.
