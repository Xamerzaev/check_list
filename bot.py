from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import PreCheckoutQuery, Message
from aiogram.dispatcher import FSMContext
import asyncio
import aiocron
import logging
import sys
from dotenv import load_dotenv
from os import getenv
from pay import order
from async_sqlite import (db_start, create_profile, edit_profile,
                          get_pending_profiles, update_profile_status,
                          get_status, update_profile_status_payment,
                          update_subscribe_period, update_end_date,
                          get_all_subscribers, create_new_room,
                          get_room_by_id, check_employee_in_room,
                          add_employee_in_room, get_room_id, get_employees,
                          get_checklist_for_user, get_checklist_for_room,
                          add_task, delete_task, get_admin_activity,
                          set_admin_activity, set_employee_activity,
                          get_employee_activity, get_room_id_by_employee_id,
                          change_task_status, get_monthly_report,
                          get_current_end_date, remove_employee, get_room_task_status,
                          block_user_access, get_all_room_owners, update_next_report_date,
                          reset_tasks_count_for_room, get_employee_name)
from keyboards import (get_keyboard, get_cancel_keyboard,
                       get_done_keyboard, get_inline_keyboard,
                       get_pay_kb, get_room_admin_kb, get_join_room_request_kb,
                       get_room_employee_kb, get_employees_kb,
                       get_employee_checklist_for_admin_kb, get_room_checklist_for_admin_kb,
                       get_room_checklist_for_employee_kb, get_my_checklist_for_employee_kb)

load_dotenv()

DAYS_IN_RATE = (30, 90, 365)
PRICES_IN_RATE = (300, 900, 3400)
TOKEN = getenv("BOT_TOKEN")
MODERATOR = getenv("ID_MODERATOR")


bot = Bot(TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


async def on_startup(_):
    await db_start()


class RoomStates(StatesGroup):
    EnterRoomID = State()
    InputTask = State()
    EnterEmployeeName = State()
    DeleteEmployee = State()
    ExitEmployee = State()
    ExitAdmin = State()


class ProfileStateGroup(StatesGroup):
    name = State()
    phone = State()
    organization = State()
    location = State()


@dp.message_handler(lambda message: message.text == "Отмена", state='*')
async def btn_cancel(message: types.Message, state: FSMContext):
    """
    Обрабатывает команду "Отмена"
    """
    current_state = await state.get_state()

    if current_state in ['RoomStates:InputTask', 'RoomStates:DeleteEmployee', 'RoomStates:ExitAdmin']:
        await state.finish()
        await message.reply('Отмена произведена!', reply_markup=get_room_admin_kb())

    elif current_state in ['RoomStates:ExitEmployee']:
        await state.finish()
        await message.reply('Отмена произведена!', reply_markup=get_room_employee_kb())
    else:
        await state.finish()
        await message.reply('Отмена произведена! Можете начать заново.', reply_markup=get_keyboard())


@dp.message_handler(lambda message: message.text == "Выход")
async def btn_exit(message: types.Message, state: FSMContext):
    """
    Обрабатывает кнопку "Выход"
    """
    user_id = message.from_user.id
    admin_status = await get_admin_activity(user_id)
    employee_status = await get_employee_activity(user_id)

    if admin_status or employee_status:
        if admin_status:
            await RoomStates.ExitAdmin.set()
            room_id = await get_room_id(user_id)
            await state.update_data(
                exit_for='admin',
                room_id=room_id
            )
            await message.reply(
                text=f"Вы действительно хотите покинуть комнату {room_id}?\n"
                     "Для подтверждения напишите слово 'Покинуть'",
                reply_markup=get_cancel_keyboard())

        elif employee_status:
            await RoomStates.ExitEmployee.set()
            room_id = await get_room_id_by_employee_id(user_id)
            if room_id:
                await state.update_data(
                    exit_for='employee',
                    room_id=room_id
                )
                await message.reply(
                    text=f"Вы действительно хотите покинуть комнату {room_id}?\n"
                         "Для подтверждения напишите слово 'Покинуть'",
                    reply_markup=get_cancel_keyboard())


@dp.message_handler(state=[RoomStates.ExitEmployee, RoomStates.ExitAdmin])
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


@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message) -> None:
    """
    Обработчик команды `/start`
    """
    if int(MODERATOR) == int(message.from_user.id):
        await message.answer(
            'Здравствуйте! Вы модератор. Вам будут высылаться заявки. \n\n'
            'Заявки будут вам отправлены как только они поступят.'
        )
    else:
        user_id = message.from_user.id
        admin_status = await get_admin_activity(user_id)
        employee_status = await get_employee_activity(user_id)
        if admin_status:
            await message.answer(
                f'Приветствую {message.from_user.full_name}! \n\n'
                'Чтобы начать взаимодействовать с ботом - '
                'выбери то, что тебе нужно.',
                reply_markup=get_room_admin_kb()
            )
        elif employee_status:
            await message.answer(
                f'Приветствую {message.from_user.full_name}! \n\n'
                'Чтобы начать взаимодействовать с ботом - '
                'выбери то, что тебе нужно.',
                reply_markup=get_room_employee_kb()
            )
        else:
            await message.answer(
                f'Приветствую {message.from_user.full_name}! \n\n'
                'Чтобы начать взаимодействовать с ботом - '
                'выбери то, что тебе нужно.',
                reply_markup=get_keyboard()
            )


@dp.message_handler(lambda message: message.text == "Помощь")
async def cmd_help(message: types.Message) -> None:
    """
    Обработчик кнопки `Помощь`
    """
    await message.reply(
        'Этот бот-ассистент создан для помощи в организации '
        'порядка в бизнесе. Вот основные шаги:\n\n'
        '1. Составление Анкеты: Вы заполняете анкету с '
        'инструкциями, предоставленными ботом, чтобы зарегистрировать'
        'свою компанию\n'
        '2. Оплата подписки: После отправки вашей анкеты, вы можете оплатить'
        'подписку через бота.\n'
        '3. Информация о Тарифах: При успешной отправке анкеты вы '
        'получите информацию о тарифах подписки.\n'
        '5. Доступ в систему: После оплаты вам будет '
        'предоставлена возможность составление основного чек-листа.\n'
        '6. После добавление сотрудника, вы сможете изменить чек-лист под него.\n\n'
        'Мы всегда готовы помочь вам на каждом этапе!'
    )


@dp.message_handler(lambda message: message.text == "Создать компанию")
async def btn_create_company(message: types.Message) -> None:
    """
    Обработчик кнопки `Создать компанию`
    """
    await message.reply(
        'Вам необходимо заполнить профиль '
        'и после успешной модерации вы сможете выбрать и оплатить '
        'подписку на определенный срок.\n\n'
        'Давайте начнем заполнять профиль Вашей компании!\n\n'
        'Продолжая диалог с ботом и предоставляя свои личные '
        'данные, вы соглашаетесь с обработкой ваших данных в '
        'соответствии с Федеральным законом "О персональных '
        'данных" от 27.07.2006 № 152-ФЗ.')
    await message.answer(text='Для начала напишите свое Имя.',
                         reply_markup=get_cancel_keyboard())
    await ProfileStateGroup.name.set()
    await create_profile(user_id=message.from_user.id)


@dp.message_handler(lambda message: message.text == "Войти в компанию")
async def btn_enter_in_company(message: types.Message) -> None:
    """
    Обработчик кнопки `Войти в компанию`
    """
    await message.reply(
        'Конечно, свяжитесь с администратором комнаты,'
        'чтобы он предоставил вам ID-комнаты\n\n'
        'Если он у вас уже имеется, введите его!')
    await message.answer(text='Введите ID комнаты',
                         reply_markup=get_cancel_keyboard())
    await RoomStates.EnterRoomID.set()


@dp.message_handler(state=RoomStates.EnterRoomID)
async def enter_room_id(message: types.Message, state: FSMContext):
    """
    Обработчик входа пользователя в комнату`
    """
    room_id = message.text
    user_id = str(message.from_user.id)
    room_data = await get_room_by_id(room_id)
    if room_data:
        if room_id == room_data[0] and user_id == room_data[1]:
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
                await RoomStates.EnterEmployeeName.set()
                await message.reply("Введите ваше имя:", reply_markup=get_cancel_keyboard())
                owner_id = room_data[1]
                await state.update_data(user_id=user_id, owner_id=owner_id, room_id=room_id)
    else:
        await message.reply("Комната с таким id не существует!")


@dp.message_handler(state=RoomStates.EnterEmployeeName)
async def process_employee_name(message: types.Message, state: FSMContext):
    """
    Обработчик ввода имени сотрудника
    """
    employee_name = message.text.strip()
    data = await state.get_data()
    room_id = data.get('room_id')
    user_id = data.get('user_id')
    owner_id = data.get('owner_id')

    await send_request_entry_to_room(user_id, employee_name, owner_id, room_id, bot)
    await message.reply("Ваша заявка отправлена на рассмотрение владельцу комнаты!")
    await state.finish()


async def send_request_entry_to_room(user_id, employee_name, owner_id, room_id, bot) -> None:
    """
    Отпавляет запрос владельцу на присоединение в комнату
    """
    await bot.send_message(
        owner_id,
        text=f'Пользователь: {employee_name} хочет присоединиться в вашу комнату',
        reply_markup=get_join_room_request_kb(user_id, room_id, employee_name)
    )


@dp.callback_query_handler(text_contains='join_room')
async def join_room_response_callback(query: types.CallbackQuery) -> None:
    """
    Обрабатывает команду Владельца комнаты "Одобрить" или "Отклонить" и отвечает пользователю
    """
    result = query.data.split(':')[1]
    employee_id = query.data.split(':')[2]
    room_id = query.data.split(':')[3]
    employee_name = query.data.split(':')[4]

    if result == 'approve':
        await add_employee_in_room(employee_id, room_id, employee_name)
        await bot.edit_message_text(
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            text="✅ Заявка одобрена"
        )
        await set_employee_activity(employee_id, 1)
        await bot.send_message(
            employee_id,
            text='Ваша заявка одобрена\nВы вошли в комнату как сотрудник!',
            reply_markup=get_room_employee_kb()
        )

    elif result == 'reject':
        await bot.send_message(
            employee_id,
            text="К сожалению Ваша заявка отклонена Владельцем комнаты. \n",
            reply_markup=get_keyboard()
        )
        await bot.edit_message_text(
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            text=" ❌ Заявка отклонена"
        )


@dp.message_handler(lambda message: message.text == "Мои сотрудники")
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


@dp.message_handler(lambda message: message.text == "Моя подписка")
async def btn_my_employees(message: types.Message) -> None:
    """
    Обработчик кнопки `Моя подписка`
    """
    user_id = message.from_user.id
    admin_status = await get_admin_activity(user_id)
    if admin_status:
        end_date = await get_current_end_date(user_id)
        await bot.send_message(
            user_id,
            text=f"Ваша подписка закончится: {end_date}\nВы также можете продлить подписку на:",
            reply_markup=get_pay_kb(user_id))


@dp.message_handler(lambda message: message.text == "Чек-лист")
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


@dp.message_handler(lambda message: message.text == "Мой Чек-лист")
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


@dp.callback_query_handler(text_contains='checklist')
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


@dp.callback_query_handler(text_contains='back')
async def back_callback_handler(query: types.CallbackQuery) -> None:
    """
    Обрабатывает кнопку 'Назад'
    """
    room_id = query.data.split(':')[1]
    employees = await get_employees(room_id)

    await bot.edit_message_reply_markup(
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        reply_markup=get_employees_kb(employees, room_id)
    )


@dp.callback_query_handler(text_contains='delete_employee')
async def delete_employee_for_admin_callback_handler(query: types.CallbackQuery, state: FSMContext) -> None:
    """
    Обрабатывает кнопку Удалить сотрудника
    """
    if await state.get_state() == RoomStates.DeleteEmployee.state:
        await query.answer("Действие уже в процессе. Ожидайте подтверждения.")
        return

    employee_id = query.data.split(':')[1]
    room_id = query.data.split(':')[2]
    employee_name = query.data.split(':')[3]

    await bot.send_message(
        chat_id=query.message.chat.id,
        text=f"Вы действительно хотите уволить {employee_name}?\n\n"
             "Все его данные и результаты за месяц будут удалены!\n\n"
             "Для подтверждения напишите слово 'Уволить'", reply_markup=get_cancel_keyboard())

    await RoomStates.DeleteEmployee.set()
    await state.update_data(employee_id=employee_id, room_id=room_id, employee_name=employee_name)


@dp.message_handler(state=RoomStates.DeleteEmployee)
async def process_employee_removal_confirmation(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    employee_id = data.get('employee_id')
    room_id = data.get('room_id')
    employee_name = data.get('employee_name')

    if message.text.strip().lower() == 'уволить':
        await remove_employee(employee_id, room_id)
        await message.reply(f"Сотрудник {employee_name} успешно уволен!", reply_markup=get_room_admin_kb())
        await bot.send_message(employee_id, text="Вы удалены из комнаты!", reply_markup=get_keyboard())
        await state.finish()
    else:
        await message.reply("Неверное слово! Попробуйте еще раз!")


@dp.callback_query_handler(text_contains='task_status')
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
            await bot.edit_message_reply_markup(
                chat_id=user_id,
                message_id=query.message.message_id,
                reply_markup=get_room_checklist_for_employee_kb(checklist)
            )

        else:
            await bot.answer_callback_query(query.id, text="Эту задачу уже выполнили!", show_alert=True)

    elif task_for == "user":
        await change_task_status(task_id, user_id)
        checklist = await get_checklist_for_user(user_id, room_id)

        await bot.edit_message_reply_markup(
            chat_id=user_id,
            message_id=query.message.message_id,
            reply_markup=get_my_checklist_for_employee_kb(checklist))


@dp.callback_query_handler(text_contains='add_task')
async def add_task_callback_handler(query: types.CallbackQuery, state: FSMContext) -> None:
    """
    Обрабатывает запрос на добавление дела
    """
    task_for = query.data.split(':')[1]
    room_id = query.data.split(':')[2]

    await query.answer()

    await query.message.answer("Введите новое дело!", reply_markup=get_cancel_keyboard())
    await RoomStates.InputTask.set()
    if task_for == 'room':
        await state.update_data(task_for=task_for, room_id=room_id)
    elif task_for == 'user':
        user_id = query.data.split(':')[3]
        await state.update_data(user_id=user_id, task_for=task_for, room_id=room_id)


@dp.message_handler(state=RoomStates.InputTask)
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
        await send_task_notification(room_id, task_description, task_for)
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


async def send_task_notification(room_id, task_description, task_for, user_id=None):
    """
    Оповещвет сотрудника о новом деле
    """
    if task_for == 'room':
        employees = await get_employees(room_id)
        for employee_id in employees:
            await bot.send_message(employee_id[0], f"Добавлено новое дело в комнату: {task_description}")
    elif task_for == 'user' and user_id:
        await bot.send_message(user_id, f"Добавлено новое дело для вас: {task_description}")


@dp.callback_query_handler(text_contains='delete_task')
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


@dp.message_handler(state=ProfileStateGroup.name)
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


@dp.message_handler(state=ProfileStateGroup.phone)
async def load_phone(message: types.Message, state: FSMContext) -> None:
    """
    Обработчик номера телефона
    """
    async with state.proxy() as data:
        data['phone'] = message.text
        await message.reply(
            'Напишите название Вашей компании.'
        )
        await ProfileStateGroup.organization.set()


@dp.message_handler(state=ProfileStateGroup.organization)
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


@dp.message_handler(state=ProfileStateGroup.location)
async def load_location(message: types.Message, state: FSMContext) -> None:
    """
    Обработчик последнего поля анкеты
    """
    async with state.proxy() as data:
        data['location'] = message.text
    user_id = message.from_user.id
    await edit_profile(state, user_id)
    await update_profile_status(user_id, status_check=0)
    await message.reply('Отлично! Вы заполнили анкету.',
                        reply_markup=get_done_keyboard())
    await state.finish()
    await start_moderation(message)


@dp.message_handler(lambda message: message.text == "Готово")
async def cmd_done(message: types.Message) -> None:
    """
    Обработчик кнопки `Готово`
    """
    await message.reply(
        'Анкета на проверке. Ожидайте результата.',
        reply_markup=get_keyboard()
    )


async def start_moderation(message: types.Message) -> None:
    """
    Начинает формирование анкеты для отправки
    """
    profiles = await get_pending_profiles()
    for profile in profiles:
        await send_profile_for_moderation(
            profile,
            MODERATOR,
            message.bot
        )
        user_id = profile[0]
        await update_profile_status(user_id, status_check=1)
        await asyncio.sleep(3)
    await bot.send_message(MODERATOR, "Все анкеты отправлены для проверки.")


async def send_profile_for_moderation(profile, moderator_id, bot) -> None:
    """
    Отпавляет профиль пользователя на модерация
    """
    user_id = profile[0]
    name = profile[1]
    phone = profile[2]
    organization = profile[3]
    location = profile[4]

    caption = f"Анкета пользователя:\n\n" \
              f"Идентификатор пользователя: {user_id}\n" \
              f"Имя: {name}\n" \
              f"Телефон: {phone}\n" \
              f"Организация: {organization}\n" \
              f"Местоположение: {location}\n\n" \

    await bot.send_message(moderator_id, text=caption,
                           reply_markup=get_inline_keyboard(user_id))


@dp.callback_query_handler(text_contains='approve')
async def approve_callback_handler(query: types.CallbackQuery) -> None:
    """
    Обрабатывает команду модеаратора "Одобрить" и отвечает пользователю
    """
    user_id = query.data.split(':')[1]
    await update_profile_status(user_id, status_check=2)
    await query.answer("Анкета одобрена.")
    await bot.edit_message_text(
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        text="✅ Заявка одобрена"
    )
    await bot.send_message(
        user_id,
        text=('Ваша заявка прошла модерацию!\n'
              'Выберите опцию подписки:'),
        reply_markup=get_pay_kb(user_id)
    )


@dp.callback_query_handler(text_contains='reject')
async def reject_callback_handler(query: types.CallbackQuery) -> None:
    """
    Обрабатывает команду модератора "Отклонить" и отвечает пользователю
    """
    user_id = query.data.split(':')[1]
    await update_profile_status(user_id, status_check=3)
    await bot.send_message(
        user_id,
        text=("К сожалению Ваша заявка отклонена модератором. \n"
              "Напишите модератору для получения более детальной информации"
              f"✉️ USER_NAME_ADMIN")
    )
    await query.answer("Анкета отклонена.")
    await bot.edit_message_text(
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        text=" ❌ Заявка отклонена"
    )


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('subscribe'))
async def handle_subscribe_callback(query: types.CallbackQuery) -> None:
    """
    Обрабатывает команды инлайн клавиатуры с тарифами
    """
    bot = query.bot
    action, user_id = query.data.split(':')
    user_status = await get_status(user_id)

    if user_status and user_status[0][8] != 3:
        if action == "subscribe_Месяц":
            await order(query.message,
                        bot,
                        'Подписка на месяц',
                        'Оформление месячной подписки',
                        PRICES_IN_RATE[0] * 100)
        elif action == "subscribe_Квартал":
            await order(query.message,
                        bot,
                        'Подписка на 3 месяца',
                        'Оформление квартальной подписки',
                        PRICES_IN_RATE[1] * 100)
        elif action == "subscribe_Год":
            await order(query.message,
                        bot,
                        'Подписка на год',
                        'Оформление годовой подписки',
                        PRICES_IN_RATE[2] * 100)
        await query.answer(f"Вы выбрали: {action.split('_')[1]}")
    else:
        await query.answer("У вас нет разрешения на совершение оплаты.")


@dp.pre_checkout_query_handler(lambda query: True)
async def process_pre_checkout_query(
        pre_checkout_query: PreCheckoutQuery) -> None:
    """
    Функция подтверждения готовности принять оплату со стороны сервера
    """
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@dp.message_handler(content_types=['successful_payment'])
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
    await update_profile_status_payment(user_id, provider_payment_charge_id)
    if message.successful_payment.total_amount == PRICES_IN_RATE[0] * 100:
        await update_subscribe_period(user_id, DAYS_IN_RATE[0])
        await update_end_date(user_id, DAYS_IN_RATE[0])
        await update_profile_status(user_id, 4)

    elif message.successful_payment.total_amount == PRICES_IN_RATE[1] * 100:
        await update_subscribe_period(user_id, DAYS_IN_RATE[1])
        await update_end_date(user_id, DAYS_IN_RATE[1])
        await update_profile_status(user_id, 5)

    elif message.successful_payment.total_amount == PRICES_IN_RATE[2] * 100:
        await update_subscribe_period(user_id, DAYS_IN_RATE[2])
        await update_end_date(user_id, DAYS_IN_RATE[2])
        await update_profile_status(user_id, 6)

    has_room = await get_room_id(user_id)
    prices_in_rate = message.successful_payment.total_amount

    if has_room:
        admin_status = await get_admin_activity(user_id)
        if admin_status == 0:
            await set_admin_activity(user_id, 1)
        await message.answer(
            text=f"Ваша подписка успешно продлена на {int(prices_in_rate / 1000)} дней!",
            reply_markup=get_room_admin_kb()
        )
    elif not has_room:
        await create_new_room(user_id)
        room_id = await get_room_id(user_id)
        if room_id:
            await set_admin_activity(user_id, 1)
            await message.answer(
                text=f"Ваша комната успешно создана!\nИдентификатор комнаты: {room_id}\nСохраните его в надежном месте.",
                reply_markup=get_room_admin_kb()
            )
        else:
            await message.answer(
                text=f"Ошибка в создании комнаты!",
                reply_markup=get_keyboard())


@aiocron.crontab('0 10 * * *')
async def check_subscriptions_and_remind() -> None:
    """
    Функция для планировщика - проверяет срок подписки за 3 дня
    и оповещает пользователя с подпиской
    """
    current_date = datetime.now().date()
    for subscriber in await get_all_subscribers():
        user_id = subscriber[0]
        end_date_str = subscriber[-2]

        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                if end_date - timedelta(days=3) == current_date:
                    await send_reminder(user_id)
                elif end_date == current_date:
                    await block_user_access(user_id)
                    await set_admin_activity(user_id, 0)
                    await bot.send_message(user_id,
                                           text='Внимание! Ваш доступ к комнате был заблокирован',
                                           reply_markup=get_keyboard())
                    await bot.send_message(user_id,
                                           text='Вы также можете продлить подписку',
                                           reply_markup=get_pay_kb(user_id))

            except ValueError as e:
                logging.error(f"Ошибка при разборе даты для пользователя {user_id}: {e}")
        else:
            logging.warning(f"Пустая строка end_date_str для пользователя {user_id}")


async def send_reminder(user_id: int) -> None:
    await bot.send_message(user_id,
                           text='Ваша подписка истекает через 3 дня!\nВы также можете продлить подписку на:',
                           reply_markup=get_pay_kb(user_id))


@aiocron.crontab('0 10 * * *')
async def check_all_monthly_reports():
    owners = await get_all_room_owners()
    for owner in owners:
        today = datetime.now().date()
        if str(today) == str(owner[3]):
            monthly_report = await get_monthly_report(user_id=owner[1], room_id=owner[0])
            if monthly_report:
                await bot.send_message(owner[1],
                                       text=f'Отчет о выполненных заданий сотрудников за прошедший месяц\n\n{monthly_report}')
            await update_next_report_date(user_id=owner[1])
            await reset_tasks_count_for_room(room_id=owner[0])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    executor.start_polling(dp,
                           skip_updates=True,
                           on_startup=on_startup)
