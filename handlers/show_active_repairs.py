from aiogram import Router, F
from aiogram.types import CallbackQuery

import services.storage as storage
from utils.keyboard import (
    main_reply_kb,
    detail_repair_inline,
)
from utils.formatter import format_repair_details

router = Router()


def register_handlers(dp):
    dp.include_router(router)





@router.callback_query(F.data.startswith("show_active_repair_details:"))
async def show_specific_active_repair_details(callback: CallbackQuery):
    repair_id = int(callback.data.split(":")[1])
    repair_data = storage.get_active_repair_data_by_id(int(repair_id))

    if repair_data:
        await callback.message.edit_text(  # Используем edit_text, чтобы заменить сообщение со списком
            format_repair_details(repair_data),
            reply_markup=detail_repair_inline(repair_id),
        )
    else:
        await callback.message.edit_text(
            "Ремонт не найден.", reply_markup=main_reply_kb()
        )

    await callback.answer()
