from aiogram.fsm.state import StatesGroup, State

class TaskState(StatesGroup):
    description = State()
    files = State()

class AdminTaskState(StatesGroup):
    rejection_reason = State()