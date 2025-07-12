import logging
import asyncio
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage

from middlewares.access_control import AccessControlMiddleware

import config

import services.storage as json_storage
from datetime import datetime, timedelta

log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
handler = TimedRotatingFileHandler(
    log_dir / "bot.log", when="midnight", interval=1, backupCount=7, encoding="utf-8"
)
handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
)

# Настраиваем корневой логгер
logging.basicConfig(level=logging.INFO, handlers=[handler, logging.StreamHandler()])

bot = Bot(
    token=config.TG_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML"),
    session=AiohttpSession(),
)

# Указываем, что будем хранить состояние FSM в оперативной памяти
# Это имя `storage` используется диспетчером aiogram
storage = MemoryStorage()

# Создаём Dispatcher и привязываем к нему storage
dp = Dispatcher(storage=storage)

dp.message.middleware(AccessControlMiddleware())
dp.callback_query.middleware(AccessControlMiddleware())

# Подключаем все роутеры (handlers)
from handlers.start_menu import router as start_menu_router
from handlers.edit_repairs import router as edit_repairs_router
from handlers.create_new_repair import router as create_new_repair_router
from handlers.show_active_repairs import router as show_active_repairs_router
from handlers.archive import router as archive_router
from handlers.reports import router as reports_router

dp.include_router(start_menu_router)
dp.include_router(edit_repairs_router)
dp.include_router(create_new_repair_router)
dp.include_router(show_active_repairs_router)
dp.include_router(archive_router)
dp.include_router(reports_router)


async def cleanup_old_archives():
    """Удаляет из архива записи старше одного года."""
    logging.info("Запуск очистки старых архивов...")
    one_year_ago = datetime.now() - timedelta(days=365)

    archive_repairs = json_storage.get_archive_repairs()

    recent_archive = [
        r
        for r in archive_repairs
        if datetime.strptime(r.get("archive_date", "01.01.1970"), "%d.%m.%Y")
        > one_year_ago
    ]

    if len(recent_archive) < len(archive_repairs):
        json_storage.update_archive_repairs(recent_archive)
        logging.info(
            f"Очистка завершена. Удалено {len(archive_repairs) - len(recent_archive)} старых записей."
        )
    else:
        logging.info("Старых записей для удаления не найдено.")


async def main():
    await cleanup_old_archives()

    while True:
        try:
            logging.info("Бот запускается...")
            await dp.start_polling(bot)
        except Exception as e:
            logging.error(f"Произошла критическая ошибка: {e}")
            logging.info("Перезапуск через 10 секунд...")
            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())
