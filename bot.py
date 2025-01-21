import os
import openai
import logging
import asyncio
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

# Проверяем, загрузились ли переменные
if not TELEGRAM_BOT_TOKEN or not OPENAI_API_KEY or not ASSISTANT_ID:
    raise ValueError("❌ Ошибка: Проверь .env файл, некоторые переменные не загружены!")

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Создаем объекты бота, диспетчера и роутера
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
router = Router()

# Хранение `thread_id` пользователей (контекст диалога)
user_threads = {}

async def get_or_create_thread(user_id):
    """Получает или создает новый thread_id для пользователя."""
    if user_id in user_threads:
        return user_threads[user_id]

    # Создаем новый поток БЕЗ project_id
    thread = openai.beta.threads.create()
    thread_id = thread.id  # ✅ Исправлено (ранее было thread["id"])

    user_threads[user_id] = thread_id
    return thread_id

async def chat_with_assistant(user_id, user_message):
    """Отправляет сообщение ассистенту и получает ответ."""
    thread_id = await get_or_create_thread(user_id)

    # Отправляем сообщение в поток
    openai.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_message
    )

    # Запускаем ассистента
    run = openai.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID
    )

    # Ждем завершения обработки
    while True:
        run_status = openai.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id  # ✅ Исправлено
        )
        if run_status.status in ["completed", "failed"]:  # ✅ Исправлено (ранее было ["completed", "failed"])
            break

    # Получаем ответ от ассистента
    messages = openai.beta.threads.messages.list(thread_id=thread_id)

    if messages and len(messages.data) > 0:  # ✅ Исправлено
        return messages.data[0].content[0].text.value  # ✅ Исправлено

    return "Ошибка: не удалось получить ответ от ассистента."

@router.message(Command("start"))
async def start_command(message: types.Message):
    """Приветственное сообщение при старте."""
    await message.answer("👋 Привет! Я бот, EdHacks. Помогу тебе написать хороший текст.Давай начнем!")

@router.message()
async def handle_message(message: types.Message):
    """Обрабатывает входящее сообщение пользователя."""
    user_id = message.from_user.id
    user_input = message.text

    response = await chat_with_assistant(user_id, user_input)
    await message.reply(response)

async def main():
    """Запуск бота (aiogram 3.x)"""
    dp.include_router(router)  # Подключаем router
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())  # Новый формат запуска для aiogram 3.x