from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(
        KeyboardButton('Создать компанию'),
        KeyboardButton('Войти в компанию'),
        KeyboardButton('Помощь'),
    )

    return kb


def get_kb_moder() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(
        KeyboardButton('Обновить')
    )

    return kb


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(
        KeyboardButton('Отмена'),
    )

    return kb


def get_room_admin_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(
        KeyboardButton('Чек-лист'),
        KeyboardButton('Мои сотрудники'),
        KeyboardButton('Моя подписка'),
        KeyboardButton('Выход'),
    )

    return kb


def get_room_employee_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(
        KeyboardButton('Чек-лист'),
        KeyboardButton('Мой Чек-лист'),
        KeyboardButton('Выход')
    )

    return kb