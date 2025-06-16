from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from aiogram.fsm.context import FSMContext
from utils.keyboard import main_reply_kb

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(state=None)
    # Пример: присылаем текст и главное меню
    await message.answer(
        "Добро пожаловать в Mexan! Выберите раздел:", reply_markup=main_reply_kb()
    )


def register_handlers(dp):
    dp.include_router(router)
