from aiogram.dispatcher.filters.state import StatesGroup, State


class ProfileStateGroup(StatesGroup):
    name = State()
    phone = State()
    organization = State()
    location = State()


class RoomState(StatesGroup):
    EnterRoomID = State()
    InputTask = State()
    EnterEmployeeName = State()
    DeleteEmployee = State()
    ExitEmployee = State()
    ExitAdmin = State()