from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import services.storage as storage
from utils.keyboard import (
    main_reply_kb,
    detail_repair_inline,
    edit_repair_options_inline,
    e_bike_problems_inline,
    select_bike_type_inline,
    edit_bike_type_inline,
    skip_notes_inline_kb,
    confirm_total_cost_kb,
    active_repairs_inline,
)
from utils.formatter import format_repair_details
from fsm_states import RepairForm, EditRepairForm

import re
from datetime import datetime

router = Router()


def register_handlers(dp):
    dp.include_router(router)


@router.message(F.text == "Действующие ремонты")
@router.message(Command("active_repairs"))
async def show_active_repairs_list(message: Message):
    active_repairs = storage.get_active_repairs()
    if not active_repairs:
        # Если ремонтов нет, предлагаем создать новый сразу
        await message.answer(
            "На данный момент нет действующих ремонтов. Хотите создать новый?",
            reply_markup=active_repairs_inline(),
        )
        return

    # Отправляем клавиатуру со списком ФИО
    await message.answer(
        "Выберите клиента для просмотра деталей ремонта:",
        reply_markup=active_repairs_inline(active_repairs),
    )

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