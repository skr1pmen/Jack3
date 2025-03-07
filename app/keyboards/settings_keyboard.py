from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo
)


def settings(url: str, mailing: bool = True):
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Изменить основную группу 📔")
            ],
            [
                KeyboardButton(text="Админ панель 🔨", web_app=WebAppInfo(url=url))
            ],
            [
                KeyboardButton(text="Отключить рассылку 📮" if mailing else "Включить рассылку 📮")
            ],
            [
                KeyboardButton(text="Сбросить базу расписаний ⭕")
            ],
            [
                KeyboardButton(text="Рассылка сообщения 💬")
            ],
            [
                KeyboardButton(text="Дополнительные группы 👥")
            ],
            [
                KeyboardButton(text="Назад ◀"),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Выберите пункт...",
        selective=True
    )


def user_settings():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Изменить группу 📔")
            ],
            [
                KeyboardButton(text="Дополнительные группы 👥")
            ],
            [
                KeyboardButton(text="Назад ◀")
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Выберите пункт...",
        selective=True
    )
