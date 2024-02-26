import logging
import sys

from aiogram.utils import executor

from services.cron_jobs import register_aiocron_jobs
from services.sql import db_start
from handlers.handlers import register_handlers
from loader import dp


async def on_startup(_):
    await db_start()
    register_handlers(dp)
    register_aiocron_jobs()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)

