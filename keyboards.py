from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardButton, InlineKeyboardMarkup)


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


def get_done_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(
        KeyboardButton('Готово'),
    )

    return kb


def get_inline_keyboard(user_id) -> InlineKeyboardMarkup:
    approve_button = InlineKeyboardButton(
        text="Одобрить",
        callback_data=f"approve:{user_id}"
    )
    reject_button = InlineKeyboardButton(
        text="Отклонить",
        callback_data=f"reject:{user_id}"
    )
    keyboard = InlineKeyboardMarkup().add(approve_button, reject_button)

    return keyboard


def get_pay_kb(user_id) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=3)
    button_1 = InlineKeyboardButton(
        text="1 месяц",
        callback_data=f"subscribe_Месяц:{user_id}")
    button_2 = InlineKeyboardButton(
        text="3 месяца",
        callback_data=f"subscribe_Квартал:{user_id}")
    button_3 = InlineKeyboardButton(
        text="1 год",
        callback_data=f"subscribe_Год:{user_id}")

    keyboard.add(button_1, button_2, button_3)

    return keyboard


def get_task_cancel_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(
        KeyboardButton('Не вводить новое дело!'),
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
        KeyboardButton('Выход'),
    )

    return kb


def get_join_room_request_kb(user_id, room_id, employee_name) -> InlineKeyboardMarkup:
    approve_button = InlineKeyboardButton(
        text="Одобрить",
        callback_data=f"join_room:approve:{user_id}:{room_id}:{employee_name}"
    )
    reject_button = InlineKeyboardButton(
        text="Отклонить",
        callback_data=f"join_room:reject:{user_id}:{room_id}:{employee_name}"
    )
    kb = InlineKeyboardMarkup().add(approve_button, reject_button)

    return kb


def get_employees_kb(employees, room_id):
    kb = InlineKeyboardMarkup()
    for employee in employees:
        kb.add(InlineKeyboardButton(
            employee[1],
            callback_data=f"checklist:{employee[0]}:{room_id}:{employee[1]}"))

    return kb


def get_employee_checklist_for_admin_kb(checklist_for_user, room_id, user_id):
    kb = InlineKeyboardMarkup(row_width=2)
    for task in checklist_for_user:
        task_row = [
            InlineKeyboardButton(task[3], callback_data=f"task"),
            InlineKeyboardButton("❌", callback_data=f"delete_task:user:{task[0]}:{room_id}:{user_id}")
        ]
        kb.add(*task_row)
    kb.add(InlineKeyboardButton("Добавить задание", callback_data=f"add_task:user:{room_id}:{user_id}"))

    return kb


def get_room_checklist_for_admin_kb(checklist, room_id):
    kb = InlineKeyboardMarkup(row_width=2)

    for task in checklist:
        task_row = [
            InlineKeyboardButton(f"{task[3]}", callback_data=f"task"),
            InlineKeyboardButton("❌", callback_data=f"delete_task:room:{task[0]}:{room_id}")
        ]
        kb.add(*task_row)
    kb.add(InlineKeyboardButton("Добавить задание", callback_data=f"add_task:room:{room_id}"))

    return kb


def get_room_checklist_for_employee_kb(checklist):
    kb = InlineKeyboardMarkup()
    for task in checklist:
        if task[4] == '1':
            kb.add(InlineKeyboardButton(text=f"{task[3]} ✅", callback_data=f"task_status:room:{task[0]}:{task[1]}"))
        else:
            kb.add(InlineKeyboardButton(text=task[3], callback_data=f"task_status:room:{task[0]}:{task[1]}"))

    return kb


def get_my_checklist_for_employee_kb(checklist):
    kb = InlineKeyboardMarkup()
    for task in checklist:
        if task[4] == '1':
            kb.add(InlineKeyboardButton(text=f"{task[3]} ✅", callback_data=f"task_status:user:{task[0]}:{task[1]}"))
        else:
            kb.add(InlineKeyboardButton(text=task[3], callback_data=f"task_status:user:{task[0]}:{task[1]}"))

    return kb
