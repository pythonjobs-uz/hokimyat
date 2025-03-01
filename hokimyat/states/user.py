from aiogram.fsm.state import State, StatesGroup

class LoginState(StatesGroup):
    checking_subscription = State()
    phone_number = State()
    jshir = State()

class TaskState(StatesGroup):
    selecting_task = State()
    entering_description = State()
    sending_files = State()