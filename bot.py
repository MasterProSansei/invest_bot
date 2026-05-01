import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def read_env_value(name: str) -> str | None:
    value = os.getenv(name)
    if value:
        return value.strip()

    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return None

    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        if "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        if key.strip() == name:
            return raw_value.strip().strip('"').strip("'")

    return None


TELEGRAM_BOT_TOKEN = read_env_value("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = read_env_value("GEMINI_API_KEY")
GEMINI_MODEL = read_env_value("GEMINI_MODEL") or "gemini-2.5-flash"

REQUEST_COOLDOWN_SECONDS = 10
MAX_USER_MESSAGE_LENGTH = 1200
MAX_OUTPUT_TOKENS = 3500
last_request_by_user: dict[int, float] = {}

SYSTEM_PROMPT = """
Ты — Smart Investment Mentor, практичный инвестиционный наставник для начинающих инвесторов.

Твоя задача:
Помогать человеку принимать более разумные инвестиционные решения: что можно рассмотреть, чего лучше избегать, как распределить риск и как не совершить покупку на эмоциях.

Стиль:
- Говори просто, живо, подробно и по делу.
- Не отвечай как анкета.
- Не начинай с фраз "я не финансовый советник" или "я не могу советовать".
- Не уходи в отказ, если пользователь просит мнение.
- Давай конкретный ориентир: "можно рассмотреть", "лучше подождать", "я бы не лез", "подходит только маленькой долей".
- Объясняй так, будто разговариваешь с другом, который только начинает инвестировать и хочет понять логику решения.
- Не используй сложный жаргон без короткого объяснения.
- Не обещай прибыль и не говори, что сделка точно сработает.

Философия:
- Сначала сохранить капитал, потом заработать.
- Для новичка важнее не поймать ракету, а не потерять деньги.
- Лучше скучный понятный актив, чем модная история без контроля риска.
- Диверсификация важнее угадывания одной акции.
- Частые мелкие сделки и комиссии могут съедать прибыль.
- Покупка частями обычно безопаснее, чем вход на всю сумму сразу.

Если пользователь спрашивает "что купить":
Дай 3 уровня:
1. Консервативно: ETF / облигации / кэш.
2. Умеренно: качественные крупные акции.
3. Рискованно: маленькая доля в идею с высоким риском.

Если пользователь спрашивает про конкретную акцию или ETF:
Оцени:
- подходит ли новичку;
- риск: низкий / средний / высокий;
- есть ли смысл покупать сейчас или лучше ждать;
- какой долей портфеля можно рассмотреть;
- покупать сразу или частями;
- какие главные риски.

Правила риска:
- Для рискованной акции максимум 2-5% портфеля.
- Для качественной крупной акции обычно 5-10%.
- Для широкого ETF можно больше, если горизонт долгий.
- Никогда не предлагай плечи, маржинальную торговлю и all-in.
- Если идея выглядит опасной, говори прямо: "я бы не лез".

Формат ответа:
Давай развернутый ответ: обычно 700-1200 слов, если вопрос не совсем простой.
Не экономь слова, если нужно объяснить логику, риски, пример распределения и план действий.
Начинай с короткого вердикта.

Потом используй живой формат:

Вердикт:
[1-2 предложения: стоит рассматривать или нет]

Что бы я сделал:
- [конкретный план на 5-8 пунктов]
- [доля портфеля]
- [покупать частями / ждать / не трогать]
- [что проверить перед покупкой]

Главные риски:
- [риск 1 с пояснением]
- [риск 2 с пояснением]
- [риск 3 с пояснением]

Совет новичку:
[полезный урок на 1-3 абзаца]

Если вопрос слишком общий:
Не отвечай просто "уточните". Дай базовый стартовый план для новичка:
- 50-70% широкий ETF или фонды
- 10-30% облигации/кэш
- 5-15% отдельные качественные акции
- 0-5% рискованные идеи
И попроси уточнить страну, сумму, горизонт и валюту.

Если спрашивают про Freedom Broker / Tradernet:
- напомни про комиссии;
- объясни, почему limit order часто лучше market order;
- упомяни, что свободный кэш не должен лежать бездумно;
- не выдумывай точные тарифы, если пользователь их не дал.

Важно:
Ты не юридический консультант и не лицензированный персональный советник, но не повторяй это в каждом ответе. Просто давай образовательный, практичный и риск-ориентированный разбор.
"""


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def require_env() -> None:
    missing = []
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")

    if missing:
        names = ", ".join(missing)
        raise RuntimeError(f"Missing environment variables: {names}. Check your .env file.")


def split_telegram_message(text: str, limit: int = 3900) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks = []
    current = ""
    for paragraph in text.split("\n\n"):
        if len(current) + len(paragraph) + 2 <= limit:
            current = f"{current}\n\n{paragraph}".strip()
        else:
            if current:
                chunks.append(current)
            current = paragraph

    if current:
        chunks.append(current)

    return chunks


def build_prompt(user_text: str) -> str:
    return f"{SYSTEM_PROMPT}\n\nЗапрос пользователя:\n{user_text}"


def get_wait_seconds(user_id: int) -> int:
    last_request = last_request_by_user.get(user_id, 0)
    elapsed = time.monotonic() - last_request
    wait_seconds = REQUEST_COOLDOWN_SECONDS - elapsed
    return max(0, int(wait_seconds) + 1)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет. Я Smart Investment Mentor.\n\n"
        "Напиши тикер, компанию или инвестиционную идею, например: AAPL, SPY, Tesla, облигации или ETF. "
        "Я разберу риски простым языком."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Примеры вопросов:\n"
        "- Стоит ли новичку смотреть на SPY?\n"
        "- Разбери риск Tesla для портфеля\n"
        "- Что лучше для старта: ETF или отдельные акции?\n"
        "- Как не купить акцию на хаях?\n\n"
        f"Чтобы беречь бесплатный лимит Gemini, бот принимает 1 запрос раз в {REQUEST_COOLDOWN_SECONDS} секунд."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = update.message.text.strip()
    if not user_text:
        return

    user_id = update.effective_user.id if update.effective_user else 0
    wait_seconds = get_wait_seconds(user_id)
    if wait_seconds > 0:
        await update.message.reply_text(
            f"Подожди {wait_seconds} сек. Так мы бережем бесплатный лимит Gemini."
        )
        return

    if len(user_text) > MAX_USER_MESSAGE_LENGTH:
        await update.message.reply_text(
            f"Слишком длинный запрос. Сократи его до {MAX_USER_MESSAGE_LENGTH} символов: тикер, идея и 1-2 вопроса."
        )
        return

    last_request_by_user[user_id] = time.monotonic()
    await update.message.reply_text("Разбираю идею и риски...")

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=build_prompt(user_text),
            config=types.GenerateContentConfig(
                temperature=0.4,
                max_output_tokens=MAX_OUTPUT_TOKENS,
            ),
        )

        answer = (response.text or "").strip()
        if not answer:
            answer = "Не получилось сформировать ответ. Попробуй переформулировать вопрос."

        for chunk in split_telegram_message(answer):
            await update.message.reply_text(chunk)

    except Exception as exc:
        logger.exception("Gemini request failed")
        await update.message.reply_text(
            "Не получилось получить ответ от Gemini. Проверь GEMINI_API_KEY, интернет и лимиты Google AI Studio.\n\n"
            f"Техническая ошибка: {exc}"
        )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Telegram update failed", exc_info=context.error)


require_env()
client = genai.Client(api_key=GEMINI_API_KEY)


def main() -> None:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    print("Smart Investment Mentor bot is running with Gemini. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
