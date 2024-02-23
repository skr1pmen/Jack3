from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton
)


def settings(mailing: bool = True):
    if mailing:
        return ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="Изменить группу 📔")
                ],
                [
                    KeyboardButton(text="Отключить рассылку 📮")
                ],
                [
                    KeyboardButton(text="Сбросить базу расписаний ⭕")
                ],
                [
                    KeyboardButton(text="Рассылка сообщения 💬")
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
    else:
        return ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="Изменить группу 📔")
                ],
                [
                    KeyboardButton(text="Включить рассылку 📮")
                ],
                [
                    KeyboardButton(text="Сбросить базу расписаний ⭕")
                ],
                [
                    KeyboardButton(text="Рассылка сообщения 💬")
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
                KeyboardButton(text="Назад ◀")
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Выберите пункт...",
        selective=True
    )
