import re

from aiogram.utils.exceptions import BotBlocked
import logging

from aiogram import types
from aiogram.types import PreCheckoutQuery, Message
from aiogram.dispatcher import FSMContext
from aiogram import Dispatcher

from config import MODERATOR, USER_NAME_ADMIN, TARIFFS
from handlers.messages import HELP_MESSAGE, CREATE_COMPANY_MESSAGE, ENTER_IN_COMPANY_MESSAGE, LEAVE_ROOM_CONFIRMATION, \
    MODERATOR_GREETING, WELCOME_MESSAGE, FIRE_EMPLOYEE_MESSAGE, APPROVAL_MESSAGE_MODERATOR, REJECTION_MESSAGE_MODERATOR
from services.utils import start_moderation, send_request_entry_to_room, send_task_notification
from services.states import RoomState, ProfileStateGroup
from services.pay import order
from services.sql import (
    create_profile, edit_profile,
    update_profile_status, update_profile_status_payment,
    update_subscribe_period, update_end_date,
    create_new_room, get_room_by_id, check_employee_in_room,
    add_employee_in_room, get_room_id, get_employees,
    get_checklist_for_user, get_checklist_for_room, add_task, delete_task,
    get_admin_activity, set_admin_activity, set_employee_activity,
    get_employee_activity, get_room_id_by_employee_id, change_task_status,
    get_current_end_date, remove_employee, get_room_task_status,
    get_employee_name, count_employees_in_room,
    get_status_check, get_task
)
from keyboards.reply_keyboards import (
    get_keyboard, get_cancel_keyboard,
    get_room_admin_kb, get_room_employee_kb)

from keyboards.inline_keyboards import (
    get_pay_kb, get_employees_kb,
    get_employee_checklist_for_admin_kb, get_room_checklist_for_admin_kb,
    get_room_checklist_for_employee_kb, get_my_checklist_for_employee_kb,
    get_pay_kb2, get_task_info_kb
)
from loader import bot


async def btn_cancel(message: types.Message, state: FSMContext):
    """
    Обрабатывает команду "Отмена"
    """
    current_state = await state.get_state()

    if current_state in ['RoomState:InputTask', 'RoomState:DeleteEmployee', 'RoomState:ExitAdmin']:
        await state.finish()
        await message.reply('Отмена произведена!', reply_markup=get_room_admin_kb())

    elif current_state in ['RoomState:ExitEmployee']:
        await state.finish()
        await message.reply('Отмена произведена!', reply_markup=get_room_employee_kb())
    else:
        await state.finish()
        await message.reply('Отмена произведена! Можете начать заново.', reply_markup=get_keyboard())


async def btn_exit(message: types.Message, state: FSMContext):
    """
    Обрабатывает кнопку "Выход"
    """
    user_id = message.from_user.id
    admin_status = await get_admin_activity(user_id)
    employee_status = await get_employee_activity(user_id)

    if admin_status:
        room_id = await get_room_id(user_id)
        await message.reply(
            text=LEAVE_ROOM_CONFIRMATION.format(room_id=room_id),
            reply_markup=get_cancel_keyboard())

        await RoomState.ExitAdmin.set()
        await state.update_data(exit_for='admin', room_id=room_id)

    elif employee_status:
        room_id = await get_room_id_by_employee_id(user_id)
        if room_id:
            await message.reply(
                text=LEAVE_ROOM_CONFIRMATION.format(room_id=room_id),
                reply_markup=get_cancel_keyboard())
            await RoomState.ExitEmployee.set()
            await state.update_data(exit_for='employee', room_id=room_id)


async def exit_confirmation(message: types.Message, state: FSMContext) -> None:
    """
    Обработчик выхода из комнаты
    """
    user_id = message.from_user.id
    data = await state.get_data()
    room_id = data.get('room_id')
    exit_for = data.get('exit_for')

    if message.text.strip().lower() == 'покинуть':
        if exit_for == 'admin':
            await set_admin_activity(user_id, 0)
        elif exit_for == 'employee':
            await set_employee_activity(user_id, 0)
        await message.reply(f"Вы покинули комнату {room_id}!", reply_markup=get_keyboard())
        await state.finish()
    else:
        await message.reply("Неверное слово! Попробуйте еще раз или нажмите кнопку 'Отменить'!")


async def cmd_start(message: types.Message) -> None:
    """
    Обработчик команды `/start`
    """
    if int(MODERATOR) == int(message.from_user.id):
        await message.answer(MODERATOR_GREETING)
    else:
        user_id = message.from_user.id
        admin_status = await get_admin_activity(user_id)
        employee_status = await get_employee_activity(user_id)

        if admin_status:
            await message.answer(WELCOME_MESSAGE.format(name=message.from_user.full_name),
                                 reply_markup=get_room_admin_kb())
        elif employee_status:
            await message.answer(WELCOME_MESSAGE.format(name=message.from_user.full_name),
                                 reply_markup=get_room_employee_kb())
        else:
            await message.answer(WELCOME_MESSAGE.format(name=message.from_user.full_name),
                                 reply_markup=get_keyboard())


async def cmd_help(message: types.Message) -> None:
    """
    Обработчик кнопки `Помощь`
    """
    await message.reply(HELP_MESSAGE)


async def btn_create_company(message: types.Message) -> None:
    """
    Обработчик кнопки `Создать компанию`
    """
    await message.reply(CREATE_COMPANY_MESSAGE)
    await message.answer(text='Для начала напишите свое Имя.',
                         reply_markup=get_cancel_keyboard())
    await ProfileStateGroup.name.set()
    await create_profile(user_id=message.from_user.id)


async def load_name(message: types.Message, state: FSMContext) -> None:
    """
    Обработчик имени
    """
    async with state.proxy() as data:
        data['name'] = message.text
        await message.reply(
            'Предоставьте ваш номер для связи'
        )
        await ProfileStateGroup.phone.set()


async def load_phone(message: types.Message, state: FSMContext) -> None:
    """
    Обработчик номера телефона
    """
    async with state.proxy() as data:
        phone_pattern = r'^(\+?7|8)?(\d{10})$'
        if re.match(phone_pattern, message.text):
            if message.text.startswith("+7"):
                data['phone'] = message.text
            elif message.text.startswith("7"):
                data['phone'] = "+" + message.text
            elif message.text.startswith("8"):
                data['phone'] = "+7" + message.text[1:]

            await message.reply('Напишите название Вашей компании.')
            await ProfileStateGroup.organization.set()
        else:
            await message.reply("Номер телефона должен начинаться с +7, 7 или 8. Пожалуйста, введите корректный номер.")


async def load_organization(message: types.Message, state: FSMContext) -> None:
    """
    Обработчик организации
    """
    async with state.proxy() as data:
        data['organization'] = message.text
        await message.answer(
            'Где находится Ваша компания?'
        )
        await ProfileStateGroup.location.set()


async def load_location(message: types.Message, state: FSMContext) -> None:
    """
    Обработчик последнего поля анкеты
    """
    async with state.proxy() as data:
        data['location'] = message.text
    user_id = message.from_user.id
    await edit_profile(state, user_id)
    await update_profile_status(user_id, status_check=0)
    await message.reply('Отлично! Вы заполнили анкету.\nАнкета на проверке. Ожидайте результата.',
                        reply_markup=get_keyboard())
    await state.finish()
    await start_moderation()


async def approve_callback_handler(query: types.CallbackQuery) -> None:
    """
    Обрабатывает команду модеаратора "Одобрить" и отвечает пользователю
    """
    user_id = query.data.split(':')[1]
    await update_profile_status(user_id, status_check=2)
    await query.answer("Анкета одобрена.")
    await query.bot.edit_message_text(
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        text="✅ Заявка одобрена"
    )

    status_check = await get_status_check(user_id)
    if status_check == 2:
        await create_new_room(user_id)
        await update_profile_status(user_id, status_check=4)
        room_id = await get_room_id(user_id)
        if room_id:
            await set_admin_activity(user_id, 1)
            try:
                await bot.send_message(user_id,
                                       text=APPROVAL_MESSAGE_MODERATOR.format(room_id=room_id),
                                       reply_markup=get_room_admin_kb())
            except BotBlocked as e:
                logging.warning(f'{user_id}: {e}')


async def reject_callback_handler(query: types.CallbackQuery) -> None:
    """
    Обрабатывает команду модератора "Отклонить" и отвечает пользователю
    """
    user_id = query.data.split(':')[1]
    await update_profile_status(user_id, status_check=3)
    try:
        await bot.send_message(
            user_id,
            text=REJECTION_MESSAGE_MODERATOR.format(name=USER_NAME_ADMIN),
            reply_markup=get_keyboard())
    except BotBlocked as e:
        logging.info(f'{user_id}: {e}')

    await query.answer("Анкета отклонена.")
    await query.bot.edit_message_text(
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        text=" ❌ Заявка отклонена"
    )


async def btn_enter_in_company(message: types.Message) -> None:
    """
    Обработчик кнопки `Войти в компанию`
    """
    await message.reply(ENTER_IN_COMPANY_MESSAGE)
    await message.answer(text='Введите ID комнаты',
                         reply_markup=get_cancel_keyboard())
    await RoomState.EnterRoomID.set()


async def enter_room_id(message: types.Message, state: FSMContext):
    """
    Обработчик входа пользователя в комнату`
    """
    room_id = message.text
    user_id = message.from_user.id
    room_data = await get_room_by_id(room_id)
    if room_data:
        if room_id == room_data[0] and int(user_id) == int(room_data[1]):
            status_check = await get_status_check(user_id)
            if status_check == 6:
                try:
                    await bot.send_message(user_id,
                                           text='Внимание! Ваш доступ к комнате был заблокирован\n\nВы также можете продлить подписку',
                                           reply_markup=get_pay_kb(user_id))
                except BotBlocked as e:
                    logging.warning(f'{user_id}: {e}')

            else:
                await set_admin_activity(user_id, 1)
                await message.reply("Вы успешно вошли в комнату как владелец!",
                                    reply_markup=get_room_admin_kb())
            await state.finish()
        else:
            if await check_employee_in_room(room_id, user_id):
                await set_employee_activity(user_id, 1)
                await message.reply("Вы успешно вошли в комнату как сотрудник!",
                                    reply_markup=get_room_employee_kb())
                await state.finish()
            else:
                await message.reply("Введите ваше имя:", reply_markup=get_cancel_keyboard())
                owner_id = room_data[1]
                await RoomState.EnterEmployeeName.set()
                await state.update_data(user_id=user_id, owner_id=owner_id, room_id=room_id)
    else:
        await message.reply("Комната с таким id не существует!")


async def process_employee_name(message: types.Message, state: FSMContext):
    """
    Обработчик ввода имени сотрудника
    """
    employee_name = message.text.strip()
    data = await state.get_data()
    room_id = data.get('room_id')
    user_id = data.get('user_id')
    owner_id = data.get('owner_id')

    await send_request_entry_to_room(user_id, employee_name, owner_id, room_id)
    await message.reply("Ваша заявка отправлена на рассмотрение владельцу комнаты!", reply_markup=get_keyboard())
    await state.finish()


async def join_room_response_callback(dp: Dispatcher, query: types.CallbackQuery) -> None:
    """
    Обрабатывает команду Владельца комнаты "Одобрить" или "Отклонить" и отвечает пользователю
    """
    bot = query.bot
    result = query.data.split(':')[1]
    employee_id = query.data.split(':')[2]
    room_id = query.data.split(':')[3]
    employee_name = query.data.split(':')[4]
    if result == 'approve':
        await bot.edit_message_text(
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            text="✅ Заявка одобрена"
        )
        await add_employee_in_room(employee_id, room_id, employee_name)
        await set_employee_activity(employee_id, 1)
        await dp.storage.reset_state(user=employee_id)
        try:
            await bot.send_message(
                employee_id,
                text='Ваша заявка одобрена\nВы вошли в комнату как сотрудник!',
                reply_markup=get_room_employee_kb()
            )
        except BotBlocked as e:
            logging.info(f'{employee_id}: {e}')

    elif result == 'reject':
        try:
            await bot.send_message(
                employee_id,
                text="К сожалению Ваша заявка отклонена Владельцем комнаты. \n",
                reply_markup=get_keyboard()
            )
        except BotBlocked as e:
            logging.info(f'{employee_id}: {e}')

        await bot.edit_message_text(
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            text=" ❌ Заявка отклонена"
        )


async def btn_my_employees(message: types.Message) -> None:
    """
    Обработчик кнопки `Мои Сотрудники`
    """
    admin_status = await get_admin_activity(message.from_user.id)
    if admin_status:
        room_id = await get_room_id(message.from_user.id)
        employees = await get_employees(room_id)

        if employees:
            await bot.send_message(
                message.from_user.id,
                text="Мои сотрудники",
                reply_markup=get_employees_kb(employees, room_id))
        else:
            await bot.send_message(message.from_user.id,
                                   text="У вас нет сотрудников")


async def btn_my_subscription(message: types.Message) -> None:
    """
    Обработчик кнопки `Моя подписка`
    """
    user_id = message.from_user.id
    admin_status = await get_admin_activity(user_id)
    if admin_status:
        end_date = await get_current_end_date(user_id)
        status_check = await get_status_check(user_id)
        found_key = next((key for key, value in TARIFFS.items() if value[-1] == status_check), None)
        if end_date:
            await bot.send_message(
                user_id,
                text=f"Ваш тариф: Сотрудников ({TARIFFS[found_key][0]})\nСрок: {TARIFFS[found_key][1]} дней\n"
                     f"Дата окончания: {end_date}\n\n"
                     f"Вы также можете продлить подписку на:",
                reply_markup=get_pay_kb(user_id))
        else:
            await bot.send_message(
                user_id,
                text=f"Вы находитель в тестовом режиме с возможностью добавления 1го сотрудника\n\nВы также можете сменить подписку:",
                reply_markup=get_pay_kb(user_id))


async def btn_checklist(message: types.Message) -> None:
    """
    Обработчик кнопки `Чек-лист`
    """
    admin_status = await get_admin_activity(message.from_user.id)
    employee_status = await get_employee_activity(message.from_user.id)

    if admin_status:
        room_id = await get_room_id(message.from_user.id)
        checklist = await get_checklist_for_room(room_id)
        await bot.send_message(
            message.from_user.id,
            text="Чек-лист",
            reply_markup=get_room_checklist_for_admin_kb(checklist, room_id))

    elif employee_status:
        room_id = await get_room_id_by_employee_id(message.from_user.id)
        checklist = await get_checklist_for_room(room_id)
        if checklist:
            await bot.send_message(
                message.from_user.id,
                text="Чек-лист",
                reply_markup=get_room_checklist_for_employee_kb(checklist))
        else:
            await bot.send_message(
                message.from_user.id,
                text="Чек-лист пуст", )


async def btn_my_checklist(message: types.Message) -> None:
    """
    Обработчик кнопки `Мой чек-лист`
    """
    employee_status = await get_employee_activity(message.from_user.id)
    if employee_status:
        room_id = await get_room_id_by_employee_id(message.from_user.id)
        if room_id:
            checklist = await get_checklist_for_user(message.from_user.id, room_id)
            if checklist:
                await bot.send_message(
                    message.from_user.id,
                    text="Мой Чек-лист",
                    reply_markup=get_my_checklist_for_employee_kb(checklist))
            else:
                await bot.send_message(
                    message.from_user.id,
                    text="Мой Чек-лист пуст", )


async def employee_checklist_for_admin_callback_handler(query: types.CallbackQuery) -> None:
    """
    Отображает список дел для конкретного сотрудника
    """
    user_id = query.data.split(':')[1]
    room_id = query.data.split(':')[2]
    employee_name = query.data.split(':')[3]
    checklist_for_user = await get_checklist_for_user(user_id, room_id)

    await bot.edit_message_text(
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        text=f"Чек-лист для {employee_name}",
        reply_markup=get_employee_checklist_for_admin_kb(checklist_for_user, room_id, user_id)
    )


async def back_callback_handler(query: types.CallbackQuery) -> None:
    """
    Обрабатывает кнопку 'Назад'
    """
    action = query.data.split(':')[1]
    if action == 'room':
        room_id = query.data.split(':')[2]
        employees = await get_employees(room_id)

        await bot.edit_message_reply_markup(
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            reply_markup=get_employees_kb(employees, room_id)
        )
    elif action == 'room_checklist':
        room_id = query.data.split(':')[2]
        checklist = await get_checklist_for_room(room_id)

        await bot.edit_message_text(
            text='Чек-лист',
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            reply_markup=get_room_checklist_for_employee_kb(checklist)
        )

    elif action == 'user_checklist':
        room_id = query.data.split(':')[2]
        employee_id = query.data.split(':')[3]
        checklist = await get_checklist_for_user(employee_id, room_id)

        await bot.edit_message_text(
            text='Мой Чек-лист',
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            reply_markup=get_room_checklist_for_employee_kb(checklist)
        )

    elif action == 'tariff':
        await bot.edit_message_reply_markup(
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            reply_markup=get_pay_kb(query.message.chat.id)
        )


async def delete_employee_for_admin_callback_handler(query: types.CallbackQuery, state: FSMContext) -> None:
    """
    Обрабатывает кнопку Удалить сотрудника
    """
    employee_id = query.data.split(':')[1]
    room_id = query.data.split(':')[2]
    employee_name = query.data.split(':')[3]

    await bot.send_message(
        chat_id=query.message.chat.id,
        text=FIRE_EMPLOYEE_MESSAGE.format(employee_name=employee_name), reply_markup=get_cancel_keyboard())

    await RoomState.DeleteEmployee.set()
    await state.update_data(employee_id=employee_id, room_id=room_id, employee_name=employee_name)


async def process_employee_removal_confirmation(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    employee_id = data.get('employee_id')
    room_id = data.get('room_id')
    employee_name = data.get('employee_name')

    if message.text.strip().lower() == 'уволить':
        await remove_employee(employee_id, room_id)
        await message.reply(f"Сотрудник {employee_name} успешно уволен!", reply_markup=get_room_admin_kb())
        try:
            await bot.send_message(employee_id, text="Вы удалены из комнаты!", reply_markup=get_keyboard())
        except BotBlocked as e:
            logging.info(f'{employee_id}: {e}')
        await state.finish()
    else:
        await message.reply("Неверное слово! Попробуйте еще раз!")


async def task_info_callback_handler(query: types.CallbackQuery) -> None:
    """
    Кнопка детали дела
    """
    user_id = query.message.chat.id

    task_id = query.data.split(':')[2]
    task = await get_task(task_id)

    await bot.edit_message_text(
        text=task[3],
        chat_id=user_id,
        message_id=query.message.message_id,
        reply_markup=get_task_info_kb(task)
    )


async def change_task_status_callback_handler(query: types.CallbackQuery) -> None:
    """
    Изменяет статус задания
    """
    user_id = query.message.chat.id
    task_for = query.data.split(':')[1]
    task_id = query.data.split(':')[2]
    room_id = query.data.split(':')[3]

    if task_for == "room":
        task_status = await get_room_task_status(task_id)
        if task_status[0] == '0' or (task_status[0] == '1' and task_status[1] == str(query.message.chat.id)):
            await change_task_status(task_id, user_id)
            checklist = await get_checklist_for_room(room_id)
            await bot.edit_message_text(
                text='Чек-лист',
                chat_id=user_id,
                message_id=query.message.message_id,
                reply_markup=get_room_checklist_for_employee_kb(checklist)
            )

        else:
            await bot.answer_callback_query(query.id, text="Эту задачу уже выполнили!", show_alert=True)

    elif task_for == "user":
        await change_task_status(task_id, user_id)
        checklist = await get_checklist_for_user(user_id, room_id)

        await bot.edit_message_text(
            text='Мой Чек-лист',
            chat_id=user_id,
            message_id=query.message.message_id,
            reply_markup=get_my_checklist_for_employee_kb(checklist))


async def add_task_callback_handler(query: types.CallbackQuery, state: FSMContext) -> None:
    """
    Обрабатывает запрос на добавление дела
    """
    task_for = query.data.split(':')[1]
    room_id = query.data.split(':')[2]

    await query.answer()

    await query.message.answer("Введите новое дело!", reply_markup=get_cancel_keyboard())
    await RoomState.InputTask.set()
    if task_for == 'room':
        await state.update_data(task_for=task_for, room_id=room_id)
    elif task_for == 'user':
        user_id = query.data.split(':')[3]
        await state.update_data(user_id=user_id, task_for=task_for, room_id=room_id)


async def process_input_task(message: types.Message, state: FSMContext) -> None:
    """
    Обрабатывает введенное пользователем дело и добавляет его
    """
    task_description = message.text

    data = await state.get_data()
    task_for = data.get('task_for')
    room_id = data.get('room_id')

    if task_for == 'room':
        await add_task(room_id, task_for, task_description)
        await bot.send_message(message.chat.id, "Дело добавлено!", reply_markup=get_room_admin_kb())
        await send_task_notification(room_id, task_description, task_for, bot)
        checklist_for_room = await get_checklist_for_room(room_id)
        await bot.send_message(chat_id=message.chat.id,
                               text="Чек-лист",
                               reply_markup=get_room_checklist_for_admin_kb(checklist_for_room, room_id))

    elif task_for == 'user':
        user_id = data.get('user_id')
        employee_name = await get_employee_name(user_id)
        await add_task(room_id, task_for, task_description, user_id)
        checklist_for_room = await get_checklist_for_user(user_id, room_id)
        await bot.send_message(message.chat.id, "Дело добавлено!", reply_markup=get_room_admin_kb())
        await send_task_notification(room_id, task_description, task_for, user_id)
        await bot.send_message(chat_id=message.chat.id,
                               text=f"Чек-лист для {employee_name}",
                               reply_markup=get_employee_checklist_for_admin_kb(checklist_for_room, room_id, user_id))

    await state.finish()


async def delete_task_callback_handler(query: types.CallbackQuery) -> None:
    """
    Удаляет дело
    """
    task_for = query.data.split(':')[1]
    task_id = query.data.split(':')[2]
    room_id = query.data.split(':')[3]

    await delete_task(task_id)

    if task_for == 'user':
        employee_id = query.data.split(':')[4]
        checklist_for_user = await get_checklist_for_user(employee_id, room_id)
        await bot.edit_message_text(chat_id=query.message.chat.id,
                                    message_id=query.message.message_id,
                                    text="Чек-лист",
                                    reply_markup=get_employee_checklist_for_admin_kb(checklist_for_user, room_id,
                                                                                     employee_id))
    elif task_for == 'room':
        checklist_for_room = await get_checklist_for_room(room_id)
        await bot.edit_message_text(chat_id=query.message.chat.id,
                                    message_id=query.message.message_id,
                                    text="Чек-лист",
                                    reply_markup=get_room_checklist_for_admin_kb(checklist_for_room, room_id))


async def handle_subscribe_callback(query: types.CallbackQuery) -> None:
    """
    Обрабатывает команды инлайн клавиатуры с тарифами
    """
    action = query.data.split(':')[1]
    count_employee = query.data.split(':')[2]
    price = query.data.split(':')[3]
    user_id = query.data.split(':')[4]
    room_id = await get_room_id(user_id)
    current_count_employees = await count_employees_in_room(room_id)
    if count_employee == 'Безлимит' or int(current_count_employees) <= int(count_employee):
        await order(query.message,
                    bot,
                    f'Подписка на {action}(Сотрудников: {count_employee})',
                    f'Оформление подписки на {action}',
                    int(price) * 100)
        await query.answer(f"Вы выбрали: {action}")
    else:
        await bot.answer_callback_query(query.id,
                                        text=f"Количество сотрудников превышает лимит тарифа.\nУ Вас сотрудников ({current_count_employees})\n\nПожалуйста, выберите другой тариф.",
                                        show_alert=True)


async def handle_subscribe_callback2(query: types.CallbackQuery) -> None:
    """
    Обрабатывает команды инлайн клавиатуры с тарифами
    """
    action = query.data.split(':')[0]
    user_id = query.data.split(':')[1]
    user_status = await get_status_check(user_id)

    if (user_status and user_status in range(41, 65)) or (user_status and user_status in (4, 6)):
        if action == "subscribe_Месяц":
            await query.message.edit_reply_markup(reply_markup=get_pay_kb2(user_id, action.split("_")[1]))
        elif action == "subscribe_Квартал":
            await query.message.edit_reply_markup(reply_markup=get_pay_kb2(user_id, action.split("_")[1]))
        elif action == "subscribe_Год":
            await query.message.edit_reply_markup(reply_markup=get_pay_kb2(user_id, action.split("_")[1]))
    else:
        await query.answer("У вас нет разрешения на совершение оплаты.")


async def process_pre_checkout_query(
        pre_checkout_query: PreCheckoutQuery) -> None:
    """
    Функция подтверждения готовности принять оплату со стороны сервера
    """
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


async def handle_successful_payment(message: Message):
    """
    Функция обрабатывает успешные платежи
    и в засимости от тарифа выполняет наполнение базы данных
    после отвечает пользователю
    """
    user_id = message.from_user.id
    provider_payment_charge_id = (
        message.successful_payment.provider_payment_charge_id
    )
    total_amount = message.successful_payment.total_amount
    tariff_info = TARIFFS[total_amount / 100]

    await update_profile_status_payment(user_id, provider_payment_charge_id)
    await update_subscribe_period(user_id, tariff_info[1])
    await update_end_date(user_id, tariff_info[1])
    await update_profile_status(user_id, tariff_info[2])

    await message.answer(
        text=f"Ваша подписка успешно продлена на {tariff_info[1]} дней!",
        reply_markup=get_room_admin_kb()
    )


async def error_handler(update, exception):
    logging.exception(f"Error in update {update}: {exception}")
    return True


def register_handlers(dp: Dispatcher) -> None:
    dp.register_message_handler(btn_cancel, lambda message: message.text == "Отмена", state='*')
    dp.register_message_handler(btn_exit, lambda message: message.text == "Выход")
    dp.register_message_handler(exit_confirmation, state=[RoomState.ExitEmployee, RoomState.ExitAdmin])
    dp.register_message_handler(cmd_start, commands=['start'])
    dp.register_message_handler(cmd_help, lambda message: message.text == "Помощь")
    dp.register_message_handler(btn_create_company, lambda message: message.text == "Создать компанию")
    dp.register_message_handler(load_name, state=ProfileStateGroup.name)
    dp.register_message_handler(load_phone, state=ProfileStateGroup.phone)
    dp.register_message_handler(load_organization, state=ProfileStateGroup.organization)
    dp.register_message_handler(load_location, state=ProfileStateGroup.location)
    dp.register_callback_query_handler(approve_callback_handler, lambda c: c.data.startswith('approve'))
    dp.register_callback_query_handler(reject_callback_handler, lambda c: c.data.startswith('reject'))
    dp.register_message_handler(btn_enter_in_company, lambda message: message.text == "Войти в компанию")
    dp.register_message_handler(enter_room_id, state=RoomState.EnterRoomID)
    dp.register_message_handler(process_employee_name, state=RoomState.EnterEmployeeName)
    dp.register_callback_query_handler(lambda query: join_room_response_callback(dp, query),
                                       lambda c: c.data.startswith('join_room'))
    dp.register_message_handler(btn_my_employees, lambda message: message.text == "Мои сотрудники")
    dp.register_message_handler(btn_my_subscription, lambda message: message.text == "Моя подписка")
    dp.register_message_handler(btn_checklist, lambda message: message.text == "Чек-лист")
    dp.register_message_handler(btn_my_checklist, lambda message: message.text == "Мой Чек-лист")
    dp.register_callback_query_handler(employee_checklist_for_admin_callback_handler, lambda c: c.data.startswith('checklist'))
    dp.register_callback_query_handler(back_callback_handler, text_contains='back')
    dp.register_callback_query_handler(delete_employee_for_admin_callback_handler, text_contains='delete_employee')
    dp.register_message_handler(process_employee_removal_confirmation, state=RoomState.DeleteEmployee)
    dp.register_callback_query_handler(task_info_callback_handler, text_contains='task_info')
    dp.register_callback_query_handler(change_task_status_callback_handler, text_contains='task_status')
    dp.register_callback_query_handler(add_task_callback_handler, text_contains='add_task')
    dp.register_message_handler(process_input_task, state=RoomState.InputTask)
    dp.register_callback_query_handler(delete_task_callback_handler, text_contains='delete_task')
    dp.register_callback_query_handler(handle_subscribe_callback, lambda c: c.data and c.data.startswith('tariff'))
    dp.register_callback_query_handler(handle_subscribe_callback2, lambda c: c.data and c.data.startswith('subscribe'))
    dp.register_pre_checkout_query_handler(process_pre_checkout_query, lambda query: True)
    dp.register_message_handler(handle_successful_payment, content_types=['successful_payment'])
    dp.register_errors_handler(error_handler)
