from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='Добавить группу', callback_data='add_group')],
            [InlineKeyboardButton(text='Удалить группу', callback_data='del_group')]
        ],
    )

def del_group(items):
    builder = InlineKeyboardBuilder()

    for key, value in items.items():
        builder.button(text=key.upper(), callback_data=f"delete_{value}")

    builder.adjust(2)
    return builder.as_markup()