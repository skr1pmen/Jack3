from aiogram.fsm.state import StatesGroup, State


class Suggestion(StatesGroup):
    suggestion = State()
