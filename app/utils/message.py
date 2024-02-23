from aiogram.fsm.state import StatesGroup, State


class Message(StatesGroup):
    message = State()
