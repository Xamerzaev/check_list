from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import PreCheckoutQuery, Message
from aiogram.dispatcher import FSMContext
from aiogram.utils.exceptions import TelegramAPIError
import aiohttp
import asyncio
import aiocron
import logging
import sys
from dotenv import load_dotenv
from os import getenv
from pay import order
# from pyro_client import add_user_to_group, send_initial_message
from async_sqlite import (db_start, create_profile, edit_profile,
                          get_pending_profiles, update_profile_status,
                          get_status, update_profile_status_payment,
                          update_subscribe_period, update_end_date,
                          get_all_subscribers, create_new_room,
                          check_room_exists, check_employee_in_room,
                          add_employee_in_room, get_room_id, get_employees,
                          get_checklist_for_user, get_checklist_for_room,
                          add_task, delete_task, get_admin_activity,
                          set_admin_activity, set_employee_activity,
                          get_employee_activity, get_room_id_by_employee_id,
                          change_room_task_status, get_monthly_report, get_current_end_date)
from keyboards import (get_keyboard, get_cancel_keyboard,
                       get_done_keyboard, get_inline_keyboard,
                       get_pay_kb, get_room_admin_kb, get_join_room_request_kb, get_room_employee_kb, get_employees_kb,
                       get_employee_checklist_for_admin_kb, get_room_checklist_for_admin_kb, get_task_cancel_kb,
                       get_room_checklist_for_employee_kb, get_my_checklist_for_employee_kb)

load_dotenv()

# PROXY_URL для обхода блокировок на PythonEveryWhere
# PROXY_URL = "http://proxy.server:3128"
notified_media_groups = {}
DAYS_IN_RATE = (30, 60, 365)
PRICES_IN_RATE = (300, 900, 3400)
TOKEN = getenv("BOT_TOKEN")
MODERATOR = getenv("ID_MODERATOR")
# GROUP_ID = getenv("GROUP_ID")
# USER_NAME_ADMIN = getenv("ADMIN")
bot = Bot(TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot,
                storage=storage)


async def on_startup(_):
    await db_start()


class RoomStates(StatesGroup):
    EnterRoomCode = State()
    InputTask = State()
    EnterEmployeeName = State()


class ProfileStateGroup(StatesGroup):
    name = State()
    phone = State()
    organization = State()
    location = State()


@dp.message_handler(lambda message: message.text == "Отмена", state='*')
async def cmd_cancel(message: types.Message, state: FSMContext):
    """
    Обрабатывает команду "Отмена"
    """
    if state is None:
        return

    await state.finish()
    await message.reply('Отмена произведена! Можете начать заново.',
                        reply_markup=get_keyboard())


@dp.message_handler(lambda message: message.text == "Не вводить новое дело!", state=RoomStates.InputTask)
async def cmd_task_cancel(message: types.Message, state: FSMContext):
    """
    Обрабатывает команду "Не вводить новое дело"
    """
    await state.finish()
    await message.reply('Отмена произведена!',
                        reply_markup=get_room_admin_kb())


@dp.message_handler(lambda message: message.text == "Выход")
async def cmd_cancel(message: types.Message):
    """
    Обрабатывает команду "Выход"
    """
    user_id = message.from_user.id
    admin_status = await get_admin_activity(user_id)
    employee_status = await get_employee_activity(user_id)

    if admin_status:
        await set_admin_activity(user_id, 0)
        await message.reply('Вы вышли из комнаты!',
                            reply_markup=get_keyboard())

    elif employee_status:
        await set_employee_activity(user_id, 0)
        await message.reply('Вы вышли из комнаты!',
                            reply_markup=get_keyboard())


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
async def cmd_create(message: types.Message) -> None:
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
async def cmd_enter_in_room(message: types.Message) -> None:
    """
    Обработчик кнопки `Войти в компанию`
    """
    await message.reply(
        'Конечно, свяжитесь с администратором комнаты,'
        'чтобы он предоставил вам ID-комнаты\n\n'
        'Если он у вас уже имеется, введите его!')
    await message.answer(text='Введите ID комнаты',
                         reply_markup=get_cancel_keyboard())
    await RoomStates.EnterRoomCode.set()


@dp.message_handler(state=RoomStates.EnterRoomCode)
async def load_room_id(message: types.Message, state: FSMContext):
    """
    Обработчик входа пользователя в комнату`
    """
    room_id = message.text
    user_id = str(message.from_user.id)
    room_and_owner = await check_room_exists(room_id)
    if room_and_owner:
        if room_id == room_and_owner[0] and user_id == room_and_owner[1]:
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
                owner_id = room_and_owner[1]
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
    employee_id = query.data.split(':')[2]
    result = query.data.split(':')[1]
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
            text="К сожалению Ваша заявка отклонена Владельцем комнаты. \n")
        await bot.edit_message_text(
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            text=" ❌ Заявка отклонена"
        )


@dp.message_handler(lambda message: message.text == "Мои сотрудники")
async def cmd_my_employees(message: types.Message) -> None:
    """
    Обработчик кнопки `Мои Сотрудники`
    """
    admin_status = await get_admin_activity(message.from_user.id)
    if admin_status:
        room_id = await get_room_id(message.from_user.id)
        employees = await get_employees(room_id)

        if employees:
            sent_message = await bot.send_message(message.from_user.id,
                                                  text="Мои сотрудники",
                                                  reply_markup=get_employees_kb(employees, room_id))
            await bot.delete_message(chat_id=sent_message.chat.id, message_id=sent_message.message_id - 1)
        else:
            await bot.send_message(message.from_user.id,
                                   text="У вас нет сотрудников")


@dp.message_handler(lambda message: message.text == "Моя подписка")
async def cmd_my_employees(message: types.Message) -> None:
    """
    Обработчик кнопки `Моя подписка`
    """
    user_id = message.from_user.id
    admin_status = await get_admin_activity(user_id)
    if admin_status:
        end_date = await get_current_end_date(user_id)
        await bot.send_message(
            user_id,
            text=f"Ваша подписка закончится: {end_date}")


@dp.message_handler(lambda message: message.text == "Чек-лист")
async def cmd_checklist(message: types.Message) -> None:
    """
    Обработчик кнопки `Чек-лист`
    """
    room_id = await get_room_id(message.from_user.id)
    if room_id:
        admin_status = await get_admin_activity(message.from_user.id)
        if admin_status:
            checklist = await get_checklist_for_room(room_id)
            await bot.send_message(
                message.from_user.id,
                text="Чек-лист",
                reply_markup=get_room_checklist_for_admin_kb(checklist, room_id))

    else:
        employee_status = await get_employee_activity(message.from_user.id)
        if employee_status:
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
async def cmd_my_checklist(message: types.Message) -> None:
    """
    Обработчик кнопки `Мой чек-лист`
    """
    employee_status = await get_employee_activity(message.from_user.id)
    if employee_status:
        room_id = await get_room_id_by_employee_id(message.from_user.id)
        if room_id:
            checklist = await get_checklist_for_user(message.from_user.id)
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
    Обрабатывает команду
    """
    user_id = query.data.split(':')[1]
    room_id = query.data.split(':')[2]
    employee_name = query.data.split(':')[3]
    checklist_for_user = await get_checklist_for_user(user_id)

    await bot.edit_message_text(
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        text=f"Чек-лист для {employee_name}",
        reply_markup=get_employee_checklist_for_admin_kb(checklist_for_user, room_id, user_id)
    )


@dp.callback_query_handler(text_contains='task_status')
async def change_task_status_callback_handler(query: types.CallbackQuery) -> None:
    """
    Изменяет статус задания
    """
    user_id = query.message.chat.id
    task_for = query.data.split(':')[1]
    task_id = query.data.split(':')[2]
    room_id = query.data.split(':')[3]
    await change_room_task_status(task_id, user_id)

    if task_for == "room":
        checklist = await get_checklist_for_room(room_id)

        await bot.edit_message_reply_markup(
            chat_id=user_id,
            message_id=query.message.message_id,
            reply_markup=get_room_checklist_for_employee_kb(checklist)
        )
    elif task_for == "user":
        checklist = await get_checklist_for_user(user_id)

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

    await query.message.answer("Введите новое дело!", reply_markup=get_task_cancel_kb())
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
                               text="Общий Чек-лист",
                               reply_markup=get_room_checklist_for_admin_kb(checklist_for_room, room_id))

    elif task_for == 'user':
        user_id = data.get('user_id')
        await add_task(room_id, task_for, task_description, user_id)
        checklist_for_room = await get_checklist_for_user(user_id)
        await bot.send_message(message.chat.id, "Дело добавлено!", reply_markup=get_room_admin_kb())
        await send_task_notification(room_id, task_description, task_for, user_id)
        await bot.send_message(chat_id=message.chat.id,
                               text=f"Чек-лист для {user_id}",
                               reply_markup=get_employee_checklist_for_admin_kb(checklist_for_room, room_id, user_id))

    await state.finish()


async def send_task_notification(room_id, task_description, task_for, user_id=None):
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
        checklist_for_user = await get_checklist_for_user(employee_id)
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
    # Вызов функции контакта админа с пользователем
    # await send_initial_message(
    #     user_id, 
    #     ('Привет! Мы добавим вас в группу сразу после оплаты,\n'
    #      'Пожалуйста удостовертесь в своих настройках чтобы мы могли Вас добавить')
    #     )


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


# Для получения ID группы - внутри группы
# @dp.message_handler(Command("group_id"))
# async def get_group_id(message: types.Message):
#     chat_id = message.chat.id
#     await message.answer(f"ID этой группы: {chat_id}")


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
        await create_new_room(user_id)

    elif message.successful_payment.total_amount == PRICES_IN_RATE[1] * 100:
        await update_subscribe_period(user_id, DAYS_IN_RATE[1])
        await update_end_date(user_id, DAYS_IN_RATE[1])
        await update_profile_status(user_id, 5)
        await create_new_room(user_id)

    elif message.successful_payment.total_amount == PRICES_IN_RATE[2] * 100:
        await update_subscribe_period(user_id, DAYS_IN_RATE[2])
        await update_end_date(user_id, DAYS_IN_RATE[2])
        await update_profile_status(user_id, 6)
        await create_new_room(user_id)

    # функция добавления пользователя в группу
    # await add_user_to_group(message.from_user.id, GROUP_ID)

    room_id = await get_room_id(user_id)
    await set_admin_activity(user_id, 1)
    await message.answer(
        text=f"Ваша комната успешно создана!\nИдентификатор комнаты: {room_id}\nСохраните его в надежном месте.",
        reply_markup=get_room_admin_kb()
    )


# async def create_new_room(message: types.Message) -> str:
#     """
#     Функция использует Telegram Api
#     для создания пригласительной ссылки с особыми параметрами
#     """
#     url = f'https://api.telegram.org/bot{TOKEN}/createChatInviteLink'
#     expire_timestamp = int((datetime.now() + timedelta(days=3)).timestamp())
#     params = {
#         'chat_id': GROUP_ID,
#         'name': 'Пригласительная',
#         'expire_date': expire_timestamp,
#         'member_limit': 1
#     }

#     async with aiohttp.ClientSession() as session:
#         async with session.post(url, json=params) as response:
#             result = await response.json()
#
#     if result['ok']:
#         invite_link = result['result']['invite_link']
#         return f'Ваша одноразовая ссылка: {invite_link}'
#     else:
#         print(f'Ошибка: {result["description"]}')
#         return 'Ошибка при создании пригласительной ссылки.' \
#                'Обратитесь к администратору'

#
# @aiocron.crontab('0 10 * * *')
# async def check_subscriptions_and_remind() -> None:
#     """
#     Функция для планировщика - проверяет срок подписки за 3 дня
#     и оповещает пользователя с подпиской
#     """
#     current_date = datetime.now().date()
#     for subscriber in await get_all_subscribers():
#         user_id = subscriber[0]
#         end_date_str = subscriber[-1]
#
#         if end_date_str:
#             try:
#                 end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
#                 if end_date - timedelta(days=3) == current_date:
#                     await send_reminder(user_id)
#                 elif end_date == current_date:
#                     await kick_user_from_group(user_id)
#             except ValueError as e:
#                 logging.error(f"Ошибка при разборе даты для пользователя {user_id}: {e}")
#         else:
#             logging.warning(f"Пустая строка end_date_str для пользователя {user_id}")
#
#
# async def send_reminder(user_id: int) -> None:
#     await bot.send_message(user_id,
#                            text='Ваша подписка истекает через три дня!',
#                            reply_markup=get_pay_kb(user_id))
#
#
# async def kick_user_from_group(user_id: int) -> None:
#     try:
#         await bot.kick_chat_member(GROUP_ID, user_id)
#     except TelegramAPIError as e:
#         print(f"Ошибка при исключении пользователя: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    executor.start_polling(dp,
                           skip_updates=True,
                           on_startup=on_startup)
