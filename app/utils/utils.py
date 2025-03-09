import asyncio
import time

from app.groups import group as group_list
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from functools import wraps

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

# Декоратор замера времени выполнения функции
def async_timer(func):
    @wraps(func)  # Сохраняем метаданные оригинальной функции
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)  # Передаём все аргументы в функцию
        end_time = time.time()
        print(f"Функция {func.__name__} выполнилась за {end_time - start_time:.4f} секунд")
        return result
    return wrapper