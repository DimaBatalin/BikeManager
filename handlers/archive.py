from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

import services.storage as storage
from utils.formatter import format_archived_repair_details
from utils.keyboard import main_reply_kb, archive_repair_inline

from aiogram.fsm.context import FSMContext


router = Router()


def register_handlers(dp):
    dp.include_router(router)


@router.message(F.text == "Архив")
async def show_archive_recent(message: Message, state: FSMContext):
    await state.set_state(state=None)
    recent_archive_list = storage.get_archived_repairs_last_two_months()

    if not recent_archive_list:
        await message.answer(
            "За последние 2 месяца нет архивированных ремонтов.",
            reply_markup=main_reply_kb(),
        )
        return

    for repair in recent_archive_list:
        await message.answer(
            format_archived_repair_details(repair),
            reply_markup=archive_repair_inline(repair.get("id")),
        )


@router.callback_query(F.data.startswith("restore_repair:"))
async def restore_repair(callback: CallbackQuery):
    if not (callback.message and callback.data):
        await callback.answer(
            "Произошла ошибка при попытке восстановить ремонт.", show_alert=True
        )
        return

    try:
        repair_id = int(callback.data.split(":")[1])
    except ValueError:
        await callback.answer("Некорректный ID ремонта.", show_alert=True)
        return

    restored = storage.restore_repair_by_id(repair_id)

    if restored:
        await callback.message.answer(
            f"Ремонт ID: {repair_id} восстановлен и перемещен в активные.",
            reply_markup=main_reply_kb(),
        )
    else:
        await callback.message.answer(
            f"Не удалось восстановить ремонт ID: {repair_id}. Возможно, он не найден в архиве.",
            reply_markup=main_reply_kb(),
        )
    await callback.answer()
