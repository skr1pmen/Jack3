import asyncio
import sys
from app.utils.utils import *

from app import config
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from app.handlers import user_handler as user
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.client.bot import DefaultBotProperties


async def main():
    bot = Bot(
        token=config.TOKEN_TEST if "--test-start" in sys.argv else config.TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    cron = AsyncIOScheduler(timezone='Europe/Moscow')
    cron.add_job(func=user.get_new_schedule, trigger='cron', minute="*/15", args=[bot])
    cron.add_job(func=user.get_statistics, trigger='cron', day_of_week="0", hour="0", minute="0", args=[bot])

    dp.include_routers(
        user.user_router,
    )

    cron.start()
    asyncio.create_task(connect_with_retry(user, bot))
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        print("Bot started")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exit")
