import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import aiosqlite
from datetime import datetime, timedelta
import os
from utils.parser import parse_human_time

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

main_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="/start"), KeyboardButton(text="/add")],
    [KeyboardButton(text="/list"), KeyboardButton(text="/delete")]
], resize_keyboard=True)

async def init_db():
    async with aiosqlite.connect("journal.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT,
                weekdays TEXT,
                time TEXT
            );
        """)
        await db.commit()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я умный бот-напоминалка 🧠⏰", reply_markup=main_kb)

@dp.message(Command("add"))
async def cmd_add(message: types.Message):
    await message.answer("Напиши напоминание в свободной форме:
Например: 'каждый понедельник в 10:00 спортзал'")

@dp.message(Command("list"))
async def cmd_list(message: types.Message):
    async with aiosqlite.connect("journal.db") as db:
        async with db.execute("SELECT message, weekdays, time FROM reminders WHERE user_id = ?", (message.from_user.id,)) as cursor:
            rows = await cursor.fetchall()
            if rows:
                response = "\n".join([f"{r[0]} — {r[1]} в {r[2]}" for r in rows])
            else:
                response = "Нет активных напоминаний."
    await message.answer(response)

@dp.message()
async def handle_text(message: types.Message):
    text = message.text
    parsed = parse_human_time(text)
    if not parsed:
        await message.answer("Не удалось понять. Попробуй: 'каждую пятницу в 19:00 фильм'")
        return
    msg, days, time_str = parsed
    async with aiosqlite.connect("journal.db") as db:
        await db.execute("INSERT INTO reminders (user_id, message, weekdays, time) VALUES (?, ?, ?, ?)",
                         (message.from_user.id, msg, days, time_str))
        await db.commit()
    await message.answer(f"✅ Напоминание добавлено: {msg} — {days} в {time_str}")

async def send_reminders():
    while True:
        now = datetime.utcnow() + timedelta(hours=3)
        check_time = (now + timedelta(minutes=30)).strftime("%H:%M")
        weekday = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][now.weekday()]
        async with aiosqlite.connect("journal.db") as db:
            async with db.execute("SELECT user_id, message, weekdays FROM reminders WHERE time = ?", (check_time,)) as cursor:
                async for row in cursor:
                    user_id, msg, days = row
                    if weekday in days.split(","):
                        try:
                            await bot.send_message(user_id, f"⏰ Через 30 минут: {msg}")
                        except:
                            pass
        await asyncio.sleep(60)

async def main():
    await init_db()
    asyncio.create_task(send_reminders())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())