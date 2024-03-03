from aiogram import Bot
from aiogram.types import Message, LabeledPrice
from dotenv import load_dotenv
from os import getenv
import json

load_dotenv()
PROVIDER_TOKEN = getenv("PROVIDER_TOKEN")


async def order(message: Message, bot: Bot, title: str,
                description: str, amount: int, phone_number:str):

    prices = [LabeledPrice(label=description, amount=amount)]
    amount_str = str(amount / 100)
    provider_data = {
        "receipt": {
            "phone_number": phone_number,
            "items": [{
                "description": "Subscribe",
                "quantity": "1.00",
                "amount": {
                    "value": amount_str,
                    "currency": "RUB"
                    },
                "vat_code": 1
            }],
        }
    }

    await bot.send_invoice(
        chat_id=message.chat.id,
        title=title,
        description=description,
        payload='Subscribe',
        provider_token=str(PROVIDER_TOKEN),
        currency='rub',
        prices=prices,
        start_parameter='ModerationNexus',
        provider_data=json.dumps(provider_data),
        need_name=True,
        need_phone_number=True,
        send_phone_number_to_provider=True,
        need_email=True,
        send_email_to_provider=True,
        need_shipping_address=False,
        is_flexible=False,
        disable_notification=False,
        reply_to_message_id=None,
        reply_markup=None
    )