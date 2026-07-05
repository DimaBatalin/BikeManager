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

logger = logging.getLogger(__name__)

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
    logger.info("Запуск очистки старых архивов...")
    one_year_ago = datetime.now() - timedelta(days=365)

    archive_repairs = json_storage.get_archive_repairs()

    recent_archive = []
    for r in archive_repairs:
        archive_date_str = r.get("archive_date", "01.01.1970")
        try:
            archive_date = datetime.strptime(archive_date_str, "%d.%m.%Y")
        except ValueError:
            # Некорректная/повреждённая дата — не удаляем запись молча,
            # а сохраняем её и логируем предупреждение, чтобы данные
            # не терялись из-за некорректного формата даты.
            logger.warning(
                "Некорректная дата архивации %r у ремонта ID:%s — запись сохранена без изменений.",
                archive_date_str,
                r.get("id"),
            )
            recent_archive.append(r)
            continue
        if archive_date > one_year_ago:
            recent_archive.append(r)

    if len(recent_archive) < len(archive_repairs):
        json_storage.update_archive_repairs(recent_archive)
        logger.info(
            "Очистка завершена. Удалено %s старых записей.",
            len(archive_repairs) - len(recent_archive),
        )
    else:
        logger.info("Старых записей для удаления не найдено.")


async def main():
    await cleanup_old_archives()

    while True:
        try:
            logger.info("Бот запускается...")
            await dp.start_polling(bot)
        except Exception:
            logger.exception("Произошла критическая ошибка при работе бота.")
            logger.info("Перезапуск через 10 секунд...")
            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())
