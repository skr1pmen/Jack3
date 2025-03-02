from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo
)


def main(url):
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Сайт 🌐", web_app=WebAppInfo(url=url)),
                KeyboardButton(text="Расписание 📅", ),
            ],
            [
                KeyboardButton(text="Звонки 🔔"),
                KeyboardButton(text="Помощь 📞"),
            ],
            [
                KeyboardButton(text="Поддержать проект 🍃",
                               web_app=WebAppInfo(url='https://www.donationalerts.com/r/skr1pmen'))
            ],
            [
                KeyboardButton(text="Предложить идею ✉")
            ],
            [
                KeyboardButton(text="Настройки ⚙"),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Выберите пункт...",
        selective=True
    )


def suggestion_idea_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отменить ввод")]],
        resize_keyboard=True,
        input_field_placeholder="Выберите пункт...",
        selective=True
    )