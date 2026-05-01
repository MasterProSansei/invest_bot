# Deploy на Scalingo бесплатно на 30 дней

Этот вариант повторяет логику из видео: проект загружается на GitHub, затем Scalingo подтягивает репозиторий и запускает Telegram-бота как `worker`.

Официально у Scalingo есть 30-дневный free trial без карты:

https://doc.scalingo.com/platform/getting-started/free-trial

## 1. Какие файлы нужны

В репозиторий загружай эти файлы:

```text
bot.py
requirements.txt
Procfile
runtime.txt
.env.example
.gitignore
README.md
README_DEPLOY_FREE.md
```

Не загружай `.env`, потому что там секретные ключи.

Важно: на GitHub нельзя загружать сам `.zip` как один файл. Нужно распаковать архив и загрузить файлы россыпью, чтобы `requirements.txt` лежал прямо в корне репозитория.

Если ты уже случайно загружал `.env` в старый репозиторий, лучше создать новый репозиторий с нуля. Удаление `.env` из GitHub не стирает его из истории коммитов.

## 2. Procfile

Уже готов:

```text
web: python -m http.server $PORT
worker: python bot.py
```

`web` нужен, чтобы Scalingo поднял приложение как web-сервис.

`worker` запускает самого Telegram-бота.

## 3. GitHub

1. Открой https://github.com/new
2. Создай новый репозиторий, например `smart-investment-mentor-bot`.
3. Можно сделать приватным.
4. Нажми `uploading an existing file`.
5. Перетащи файлы из списка выше.
6. Нажми `Commit changes`.

## 4. Scalingo

1. Открой https://scalingo.com
2. Создай аккаунт.
3. Нажми `Create an application`.
4. Выбери регион.
5. Придумай название приложения.
6. Подключи GitHub через `Link repo`.
7. Выбери свой репозиторий.
8. Оставь ветку `main`.
9. Нажми `Finish`.

## 5. Environment

В Scalingo открой вкладку `Environment` и добавь переменные:

```env
TELEGRAM_BOT_TOKEN=токен_от_BotFather
GEMINI_API_KEY=ключ_от_Google_AI_Studio
GEMINI_MODEL=gemini-2.5-flash
BUILDPACK_NAME=python
```

## 6. Deploy

1. Открой вкладку `Deploy`.
2. Нажми `Manual deploy`.
3. Выбери ветку `main`.
4. Нажми `Trigger deploy`.

## 7. Resources

После успешного деплоя:

1. Открой `Resources`.
2. У процесса `worker` поставь количество `1`.
3. Нажми `Scale`.

Если `worker` стоит `0`, Telegram-бот не будет отвечать.

## 8. Проверка

Открой Telegram-бота и отправь:

```text
/start
```

Потом:

```text
Что купить новичку на 1000 долларов?
```

## 9. Важно

После окончания 30-дневного trial Scalingo downscale-ит приложение до 0 контейнеров, если не добавить оплату. Это не вечный бесплатный хостинг.
