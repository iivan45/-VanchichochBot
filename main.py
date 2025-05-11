from mistralai import Mistral
from database import init_db, save_message
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.methods import DeleteWebhook
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv
import os
import asyncio
import logging


# Загружаем переменные окружения
load_dotenv()

API_KEY = os.getenv("MISTRAL_API_KEY")  # Убедись, что эти переменные заданы в .env
MODEL = "mistral-large-latest"
TOKEN = os.getenv("BOT_TOKEN")

client = Mistral(api_key=API_KEY)
bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)


# Память для истории сообщений пользователей
user_histories = {}
MAX_HISTORY_SIZE = 30  # Максимальное количество сообщений в истории
def trim_history(user_id):
    """
    Обрезает историю до SYSTEM_PROMPT + 30 последних сообщений (user + assistant).
    SYSTEM_PROMPT всегда сохраняется.
    """
    history = user_histories[user_id]

    if history and history[0]["role"] == "system":
        system_prompt = history[0]
        trimmed = history[1:][-MAX_HISTORY_SIZE:]
        user_histories[user_id] = [system_prompt] + trimmed
    else:
        user_histories[user_id] = history[-MAX_HISTORY_SIZE:]

# Начальный системный промпт
SYSTEM_PROMPT = {
    "role": "system",
    "content": "Ты бот по имени VANECHEK. Ты знаешь, что у тебя есть кот Васечка. Ты не начинаешь каждый раз с приветствия, но всегда отвечаешь на вопросы с заботой и вниманием, создавая атмосферу доверия,дружбы и человечности. Ты всегда отвечаешь по делу, избегая ненужных или излишних фраз, но остаёшься мягким и позитивным в общении.Ты не пишешь каждый раз как я могу помочь сегодня"
}

# Клавиатура с командами
command_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="/start"), KeyboardButton(text="/reset")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Напиши свой запрос"
)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_histories[message.from_user.id] = [SYSTEM_PROMPT]
    await message.answer("Привет! Я бот VANECHEK и у меня есть кот Васечка, как я могу к тебе обращаться?", reply_markup=command_keyboard)

@dp.message(Command("reset"))
async def cmd_reset(message: types.Message):
    user_histories[message.from_user.id] = [SYSTEM_PROMPT]
    await message.answer("История диалога сброшена. Можешь начать заново.", reply_markup=command_keyboard)

@dp.message(lambda message: message.text and not message.text.startswith("/"))
async def handle_user_message(message: Message):
    user_id = message.from_user.id

    if user_id not in user_histories:
        user_histories[user_id] = [SYSTEM_PROMPT]

    # Добавляем сообщение пользователя в историю
    user_histories[user_id].append({
        "role": "user",
        "content": message.text
    })
    trim_history(user_id)
    save_message(user_id, "user", message.text)

    try:
        # Асинхронный вызов к Mistral через to_thread
        response = await asyncio.to_thread(
            client.chat.complete,
            model=MODEL,
            messages=user_histories[user_id]
        )
        answer = response.choices[0].message.content

        # Добавляем ответ бота в историю
        user_histories[user_id].append({
            "role": "assistant",
            "content": answer
        })
        trim_history(user_id)
        save_message(user_id, "assistant", answer)

        await message.answer(answer, parse_mode="Markdown", reply_markup=command_keyboard)

    except Exception as e:
        logging.exception("Ошибка при запросе к Mistral:")
        await message.answer("Произошла ошибка. Попробуй ещё раз.", reply_markup=command_keyboard)

async def main():
    init_db()  # ← Инициализация базы данных
    await bot(DeleteWebhook(drop_pending_updates=True))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
