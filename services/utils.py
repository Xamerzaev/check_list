import asyncio
import logging

from aiogram.utils.exceptions import BotBlocked
from aiogram.dispatcher import FSMContext
from aiogram import types

from loader import bot, dp
from config import MODERATOR, TARIFFS
from keyboards.inline_keyboards import get_inline_keyboard, get_join_room_request_kb, get_pay_kb
from services.sql import get_pending_profiles, update_profile_status, count_employees_in_room, get_status_check, \
    get_employees


async def start_moderation() -> None:
    """
    Начинает формирование анкеты для отправки
    """
    profiles = await get_pending_profiles()
    for profile in profiles:
        await send_profile_for_moderation(
            profile,
            MODERATOR
        )
        user_id = profile[0]
        await update_profile_status(user_id, status_check=1)
        await asyncio.sleep(3)
    await bot.send_message(MODERATOR, "Все анкеты отправлены для проверки.")


async def send_profile_for_moderation(profile, moderator_id) -> None:
    """
    Отправляет профиль пользователя на модерация
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


async def send_request_entry_to_room(user_id, employee_name, owner_id, room_id) -> None:
    """
    Отправляет запрос владельцу на присоединение в комнату
    """
    count_employees = await count_employees_in_room(room_id)
    status_check = await get_status_check(owner_id)
    if status_check == 4 and count_employees < 1:
        try:
            await bot.send_message(
                owner_id,
                text=f'Пользователь {employee_name} хочет присоединиться в вашу комнату',
                reply_markup=get_join_room_request_kb(user_id, room_id, employee_name)
            )
        except BotBlocked as e:
            logging.info(f'{user_id}: {e}')

    elif 41 <= status_check <= 64:
        for tariff in TARIFFS.values():
            if tariff[2] == status_check and count_employees < tariff[0]:
                try:
                    await bot.send_message(
                        owner_id,
                        text=f'Пользователь {employee_name} хочет присоединиться в вашу комнату',
                        reply_markup=get_join_room_request_kb(user_id, room_id, employee_name)
                    )
                except BotBlocked as e:
                    logging.info(f'{user_id}: {e}')
    else:
        try:
            await bot.send_message(
                owner_id,
                text=f'Пользователь {employee_name} хочет присоединиться в вашу комнату!\n'
                     f'Вы не можете принять либо отклонить, так как у вас превышен лимит сотрудников!\n'
                     f'Вы можете улучшить подписку и попросить повторить попытку сотрудника.',
                reply_markup=get_pay_kb(owner_id)
            )
        except BotBlocked as e:
            logging.info(f'{user_id}: {e}')


async def send_task_notification(room_id, task_description, task_for, user_id=None):
    """
    Оповещвет сотрудника о новом деле
    """
    if task_for == 'room':
        employees = await get_employees(room_id)
        for employee_id in employees:
            try:
                await bot.send_message(employee_id[0], f"✅ Добавлено новое дело в комнату: {task_description}")
            except BotBlocked as e:
                logging.info(f'{employee_id[0]}: {e}')
    elif task_for == 'user' and user_id:
        try:
            await bot.send_message(user_id, f"✅ Добавлено новое дело для вас: {task_description}")
        except BotBlocked as e:
            logging.info(f'{user_id}: {e}')
