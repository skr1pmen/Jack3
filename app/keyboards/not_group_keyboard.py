from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
)


def main():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Я пока не студент колледжа 🎓"),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Название группы...",
        selective=True
    )
