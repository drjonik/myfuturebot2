import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import aiosqlite
from datetime import datetime, time, timedelta
import os

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

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
async def start(message: types.Message):
    await message.answer("Привет! Я твой бот-дневник с напоминаниями.\nИспользуй команду /напоминание чтобы добавить задачу.")

@dp.message(Command("напоминание"))
async def reminder(message: types.Message):
    try:
        parts = message.text.split(" ", 3)
        if len(parts) < 4:
            await message.answer("Формат: /напоминание ТЕКСТ ДНИ ЧАСЫ:МИНУТЫ\nПример: /напоминание Зал Пн,Ср,Пт 15:00")
            return
        _, msg, days, time_str = parts
        async with aiosqlite.connect("journal.db") as db:
            await db.execute("INSERT INTO reminders (user_id, message, weekdays, time) VALUES (?, ?, ?, ?)",
                             (message.from_user.id, msg, days, time_str))
            await db.commit()
        await message.answer(f"✅ Напоминание добавлено: {msg} — {days} в {time_str}")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

async def send_reminders():
    while True:
        now = datetime.now()
        check_time = (now + timedelta(minutes=30)).strftime("%H:%M")
        weekday = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][now.weekday()]
        async with aiosqlite.connect("journal.db") as db:
            async with db.execute("SELECT user_id, message FROM reminders WHERE time = ?", (check_time,)) as cursor:
                async for row in cursor:
                    user_id, msg = row
                    async with db.execute("SELECT weekdays FROM reminders WHERE user_id = ? AND message = ?", (user_id, msg)) as day_cursor:
                        weekdays_row = await day_cursor.fetchone()
                        if weekdays_row and weekday in weekdays_row[0]:
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