import logging

from aiogram import Bot
from aiogram.types import Message, LabeledPrice
from config import PROVIDER_TOKEN


async def order(message: Message, bot: Bot, title: str, description: str, amount: int):
    try:
        prices = [LabeledPrice(label=description, amount=amount)]
        await bot.send_invoice(
            chat_id=message.chat.id,
            title=title,
            description=description,
            payload='Subscribe',
            provider_token=str(PROVIDER_TOKEN),
            currency='rub',
            prices=prices,
            start_parameter='ModerationNexus',
            provider_data=None,
            need_name=True,
            need_phone_number=True,
            need_email=True,
            need_shipping_address=False,
            send_phone_number_to_provider=False,
            is_flexible=False,
            disable_notification=False,
            reply_to_message_id=None,
            reply_markup=None
        )
    except Exception as e:
        logging.error(f'order: {e}')
