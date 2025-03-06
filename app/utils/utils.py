import asyncio

from app.groups import group as group_list
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

async def connect_with_retry(user, bot, retries=10, delay=30):
    for attempt in range(retries):
        try:
            await user.connect_to_server(bot)
            print("Connected successfully!")
            return  # Успешное подключение, выходим из функции
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                print(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)  # Не блокируем event loop
            else:
                print("All attempts failed.")
                raise

async def get_group_name_by_class_code(class_code):
    return [key for key in group_list if group_list[key] == class_code][0]
