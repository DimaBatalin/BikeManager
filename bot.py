import logging
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage

from middlewares.access_control import AccessControlMiddleware

import config

# Уровень логирования
logging.basicConfig(level=logging.INFO)

# Инициализируем Bot с токеном и HTML-парсингом
bot = Bot(
    token=config.TG_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML"),
    session=AiohttpSession(),
)

# Указываем, что будем хранить состояние FSM в оперативной памяти
storage = MemoryStorage()

# Создаём Dispatcher и привязываем к нему storage
dp = Dispatcher(storage=storage)

dp.message.middleware(AccessControlMiddleware())
dp.callback_query.middleware(AccessControlMiddleware())

# Подключаем все роутеры (handlers)
from handlers.start_menu import router as start_menu_router
from handlers.active_repairs import router as active_repairs_router
from handlers.archive import router as archive_router
from handlers.reports import router as reports_router

dp.include_router(start_menu_router)
dp.include_router(active_repairs_router)
dp.include_router(archive_router)
dp.include_router(reports_router)


async def main():    
    while True:
        try:
            await dp.start_polling(bot)
        except asyncio.exceptions.CancelledError:
            break
        finally:
            await dp.stop_polling()
    


if __name__ == "__main__":
    asyncio.run(main())
