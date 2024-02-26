from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import TARIFFS


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


def get_pay_kb2(user_id, action) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=3)
    for price, (num_employees, duration, code) in TARIFFS.items():
        if action == 'Месяц' and duration == 30:
            keyboard.add(InlineKeyboardButton(
                text=f"Сотрудников ({num_employees})",
                callback_data=f"tariff:{action}:{num_employees}:{price}:{user_id}"))
        elif action == 'Квартал' and duration == 90:
            keyboard.add(InlineKeyboardButton(
                text=f"Сотрудников ({num_employees})",
                callback_data=f"tariff:{action}:{num_employees}:{price}:{user_id}"))
        elif action == 'Год' and duration == 365:
            keyboard.add(InlineKeyboardButton(
                text=f"Сотрудников ({num_employees})",
                callback_data=f"tariff:{action}:{num_employees}:{price}:{user_id}"))
    keyboard.add(InlineKeyboardButton(text=f"Назад", callback_data=f"back:tariff"))
    return keyboard


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


def get_employees_kb(employees, room_id) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    for employee in employees:
        employee_row = [
            InlineKeyboardButton(employee[1], callback_data=f"checklist:{employee[0]}:{room_id}:{employee[1]}"),
            InlineKeyboardButton('Удалить', callback_data=f"delete_employee:{employee[0]}:{room_id}:{employee[1]}")
        ]
        kb.add(*employee_row)

    return kb


def get_employee_checklist_for_admin_kb(checklist_for_user, room_id, employee_id) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    for task in checklist_for_user:
        task_row = [
            InlineKeyboardButton(task[3], callback_data=f"task"),
            InlineKeyboardButton("❌", callback_data=f"delete_task:user:{task[0]}:{room_id}:{employee_id}")
        ]
        kb.add(*task_row)
    kb.add(InlineKeyboardButton("Добавить задание", callback_data=f"add_task:user:{room_id}:{employee_id}"))
    kb.add(InlineKeyboardButton("Назад", callback_data=f"back:{room_id}:{room_id}"))

    return kb


def get_room_checklist_for_admin_kb(checklist, room_id) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)

    for task in checklist:
        task_row = [
            InlineKeyboardButton(f"{task[3]}", callback_data=f"task"),
            InlineKeyboardButton("❌", callback_data=f"delete_task:room:{task[0]}:{room_id}")
        ]
        kb.add(*task_row)
    kb.add(InlineKeyboardButton("Добавить задание", callback_data=f"add_task:room:{room_id}"))

    return kb


def get_room_checklist_for_employee_kb(checklist) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    for task in checklist:
        if task[4] == '1':
            kb.add(InlineKeyboardButton(text=f"{task[3]} ✅", callback_data=f"task_status:room:{task[0]}:{task[1]}"))
        else:
            kb.add(InlineKeyboardButton(text=task[3], callback_data=f"task_status:room:{task[0]}:{task[1]}"))

    return kb


def get_my_checklist_for_employee_kb(checklist) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    for task in checklist:
        if task[4] == '1':
            kb.add(InlineKeyboardButton(text=f"{task[3]} ✅", callback_data=f"task_status:user:{task[0]}:{task[1]}"))
        else:
            kb.add(InlineKeyboardButton(text=task[3], callback_data=f"task_status:user:{task[0]}:{task[1]}"))

    return kb
