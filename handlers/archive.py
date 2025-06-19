from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import services.storage as storage
from utils.formatter import format_archived_repair_details
from utils.keyboard import main_reply_kb, archive_pagination_kb
from datetime import datetime

from fsm_states import EditArchiveForm

router = Router()


def register_handlers(dp):
    dp.include_router(router)


@router.message(F.text == "Архив")
async def show_archive_paginated(message: Message, state: FSMContext):
    await state.clear()
    await process_archive_page(message, 0)


@router.callback_query(F.data.startswith("archive_page:"))
async def handle_archive_pagination(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    # Важно: используем callback.message, чтобы отредактировать существующее сообщение
    await process_archive_page(callback.message, page, is_edit=True)
    await callback.answer()


async def process_archive_page(message: Message, page: int, is_edit: bool = False):
    repairs_list = storage.get_archived_repairs_last_two_months()

    if not repairs_list:
        await message.answer(
            "За последние 2 месяца нет архивированных ремонтов.",
            reply_markup=main_reply_kb(),
        )
        return

    # Сортируем по дате, чтобы новые были сверху
    repairs_list.sort(
        key=lambda r: datetime.strptime(
            r.get("archive_date", "01.01.1970"), "%d.%m.%Y"
        ),
        reverse=True,
    )

    total_pages = len(repairs_list)
    if page < 0 or page >= total_pages:
        return  # Выход, если страница недействительна

    repair = repairs_list[page]
    repair_id = repair.get("id")

    text = format_archived_repair_details(repair)
    keyboard = archive_pagination_kb(page, total_pages, repair_id)

    if is_edit:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


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


@router.callback_query(F.data.startswith("delete_repair:"))
async def delete_repair(callback: CallbackQuery):
    try:
        repair_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("Ошибка ID ремонта.", show_alert=True)
        return

    deleted = storage.delete_repair_from_archive_by_id(repair_id)

    if deleted:
        await callback.message.edit_text(f"Ремонт ID: {repair_id} был удален навсегда.")
    else:
        await callback.message.answer("Не удалось удалить ремонт.")

    await callback.answer()


@router.callback_query(F.data.startswith("edit_archive_date:"))
async def edit_archive_date_start(callback: CallbackQuery, state: FSMContext):
    try:
        repair_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("Ошибка ID ремонта.", show_alert=True)
        return

    await state.set_state(EditArchiveForm.waiting_for_date)
    await state.update_data(repair_id_to_edit=repair_id)

    await callback.message.answer("Введите новую дату архивации в формате ДД.ММ.ГГГГ:")
    await callback.answer()


@router.message(EditArchiveForm.waiting_for_date)
async def process_new_archive_date(message: Message, state: FSMContext):
    new_date_str = message.text
    try:
        # Проверяем, что дата в правильном формате
        datetime.strptime(new_date_str, "%d.%m.%Y")
    except ValueError:
        await message.answer("Неверный формат. Введите дату в формате ДД.ММ.ГГГГ:")
        return

    user_data = await state.get_data()
    repair_id = user_data.get("repair_id_to_edit")

    if not repair_id:
        await message.answer(
            "Произошла ошибка, ID ремонта не найден. Попробуйте снова."
        )
        await state.clear()
        return

    updated = storage.update_archive_repair_field(
        repair_id, "archive_date", new_date_str
    )

    if updated:
        await message.answer(
            f"Дата архивации для ремонта ID:{repair_id} обновлена на {new_date_str}."
        )
    else:
        await message.answer("Не удалось обновить дату.")

    await state.clear()
