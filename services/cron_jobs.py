from os import path, remove
from datetime import datetime, timedelta
import logging

import aiocron
from aiogram.utils.exceptions import BotBlocked

from keyboards.inline_keyboards import get_pay_kb
from keyboards.reply_keyboards import get_keyboard
from services.sql import (get_all_subscribers, get_room_owners,
                          clear_task_completion, reset_task_status,
                          block_user_access, set_admin_activity)
from services.report import generate_pdf_report
from loader import bot


async def check_subscriptions_and_remind() -> None:
    """
    Функция для планировщика - проверяет срок подписки за 3 дня
    и оповещает пользователя с подпиской
    """
    current_date = datetime.now().date()
    for subscriber in await get_all_subscribers():
        user_id = subscriber[0]
        end_date_str = subscriber[9]

        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                if end_date - timedelta(days=3) == current_date:
                    try:
                        await bot.send_message(
                            user_id,
                            text='Ваша подписка истекает через 3 дня!\nВы также можете продлить подписку на:',
                            reply_markup=get_pay_kb(user_id)
                        )
                    except BotBlocked as e:
                        logging.info(f'{user_id}: {e}')

                elif end_date == current_date:
                    await block_user_access(user_id)
                    await set_admin_activity(user_id, 0)
                    try:
                        await bot.send_message(user_id,
                                               text='Внимание! Ваш доступ к комнате был заблокирован',
                                               reply_markup=get_keyboard())
                        await bot.send_message(user_id,
                                               text='Вы также можете продлить подписку',
                                               reply_markup=get_pay_kb(user_id))
                    except BotBlocked as e:
                        logging.info(f'{user_id}: {e}')

            except ValueError as e:
                logging.error(f"Ошибка при разборе даты для пользователя {user_id}: {e}")
        else:
            logging.warning(f"Пустая строка end_date_str для пользователя {user_id}")


async def send_monthly_reports() -> None:
    """
    Отправляеть месячный отчет в PDF файле каждому владельцу компании
    """
    owners = await get_room_owners()
    for owner in owners:
        await generate_pdf_report(room_id=owner[0])
        file_name = f"report_{owner[0]}.pdf"
        if path.exists(file_name):
            try:
                await bot.send_document(owner[1], document=open(file_name, "rb"))
                remove(file_name)
            except BotBlocked as e:
                logging.info(f'{owner[1]}: {e}')
    await clear_task_completion()


async def update_tasks_status():
    """
    Сохраняет данные за прошедший день и сбрасываеет статусы заданий
    """
    await reset_task_status()


def register_aiocron_jobs():
    aiocron.crontab('0 10 * * *')(check_subscriptions_and_remind)
    aiocron.crontab('1 0 1 * *')(send_monthly_reports)
    aiocron.crontab('0 0 * * *')(update_tasks_status)
