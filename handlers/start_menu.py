from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from utils.keyboard import main_reply_kb
from handlers.active_repairs import show_active_repairs_list
from handlers.archive import show_archive_recent
from handlers.reports import show_report_options

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    # Пример: присылаем текст и главное меню
    await message.answer(
        "Добро пожаловать в Mexan! Выберите раздел:", reply_markup=main_reply_kb()
    )


def register_handlers(dp):
    dp.include_router(router)
