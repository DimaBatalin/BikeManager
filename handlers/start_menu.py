from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from aiogram.fsm.context import FSMContext
import services.storage as storage
from utils.keyboard import (
    main_reply_kb,
    source_filter_inline_kb,
    active_repairs_inline,
)
from fsm_states import RepairForm

router = Router()


def register_handlers(dp):
    dp.include_router(router)


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(state=None)
    await message.answer(
        "Добро пожаловать в Mexan! Выберите раздел:", reply_markup=main_reply_kb()
    )


@router.message(F.text == "➕ Создать новый ремонт")
@router.message(Command("add_repair"))
@router.callback_query(F.data == "new_repair")
@router.callback_query(F.data == "new_repair_from_empty")
async def start_add_repair(
    update: types.Union[Message, CallbackQuery], state: FSMContext
):
    """Начало процесса создания нового ремонта, запрашивает ФИО."""
    if isinstance(update, Message):
        await update.answer("Введите ФИО клиента:")
    elif isinstance(update, CallbackQuery):
        await update.message.edit_text("Введите ФИО клиента:")
        await update.answer()

    await state.set_state(RepairForm.fio)


@router.message(F.text == "Архив")
async def show_archive_filter(message: Message, state: FSMContext):
    """Сначала показывает фильтр, потом архив."""
    await state.clear()
    await message.answer(
        "🗂️ Выберите категорию для просмотра архива:",
        reply_markup=source_filter_inline_kb(prefix="archive_filter"),
    )


@router.message(F.text == "Отчёты")
async def show_report_source_filter(message: Message, state: FSMContext):
    """
    Сначала показывает фильтр по источнику.
    """
    await state.clear()
    await message.answer(
        "📊 Выберите категорию для формирования отчёта:",
        reply_markup=source_filter_inline_kb(prefix="report_filter"),
    )


@router.message(F.text == "Действующие ремонты")
@router.message(Command("active_repairs"))
async def show_active_repairs_list(message: Message, state: FSMContext):
    await state.set_state(state=None)
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
