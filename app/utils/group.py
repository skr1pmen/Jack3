from aiogram.fsm.state import StatesGroup, State


class Group(StatesGroup):
    group = State()

class AddGroup(StatesGroup):
    additional_group = State()
