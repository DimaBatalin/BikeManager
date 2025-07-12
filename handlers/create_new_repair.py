from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import services.storage as storage
from utils.keyboard import (
    detail_repair_inline,
    e_bike_problems_inline,
    select_bike_type_inline,
    skip_notes_inline_kb,
    confirm_total_cost_kb,
    select_repair_source_inline,
)
from utils.formatter import format_repair_details, parse_breakdowns_with_cost
from fsm_states import RepairForm, EditRepairForm

import re
from datetime import datetime

router = Router()


def register_handlers(dp):
    dp.include_router(router)


def parse_breakdowns_with_cost(text: str) -> tuple[list[str], int]:
    """
    Разбирает строку с поломками и их стоимостью.
    Пример: 'Ремонт колеса 500, замена цепи 1200'
    Возвращает список строк поломок и общую стоимость.
    """
    breakdowns_list = []
    total_cost = 0
    parts = [part.strip() for part in text.split(",")]
    for part in parts:
        match = re.search(r"\s+(\d+)$", part)
        if match:
            cost = int(match.group(1))
            breakdowns_list.append(part)
            total_cost += cost
        else:
            breakdowns_list.append(part)
    return breakdowns_list, total_cost





@router.message(RepairForm.fio)
async def process_fio(message: Message, state: FSMContext):
    """Сохраняет ФИО и запрашивает источник ремонта."""
    await state.update_data(FIO=message.text)
    await state.set_state(RepairForm.repair_type)
    await message.answer(
        "Выберите источник:", reply_markup=select_repair_source_inline()
    )


@router.callback_query(F.data.startswith("set_source:"), RepairForm.repair_type)
async def process_repair_source(callback: CallbackQuery, state: FSMContext):
    """Сохраняет источник и запрашивает контакт."""
    source = callback.data.split(":")[1]
    await state.update_data(repair_type=source)
    await state.set_state(RepairForm.contact)
    await callback.message.edit_text("Введите контактный телефон клиента:")
    await callback.answer()


@router.message(RepairForm.contact)
async def process_contact(message: Message, state: FSMContext):
    """Сохраняет контакт и запрашивает тип велосипеда."""
    await state.update_data(contact=message.text)
    await state.set_state(RepairForm.bike_type)
    await message.answer(
        "Выберите тип велосипеда:", reply_markup=select_bike_type_inline()
    )


@router.callback_query(F.data.startswith("set_bike_type:"), RepairForm.bike_type)
async def process_bike_type(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор типа велосипеда и направляет на следующий шаг."""
    bike_type_str = callback.data.split(":")[1]
    is_mechanics = bike_type_str == "mechanics"
    await state.update_data(isMechanics=is_mechanics)

    if not is_mechanics:  # Электровелосипед
        await state.update_data(namebike="Электровелосипед", breakdowns=[])
        await state.set_state(RepairForm.e_bike_breakdowns_select)
        await callback.message.edit_text(
            "Тип: Электровелосипед.\nВыберите стандартные поломки или введите свои:",
            reply_markup=e_bike_problems_inline([]),
        )
    else:  # Механический велосипед
        await state.set_state(RepairForm.namebike)
        await callback.message.edit_text("Введите название велосипеда:")

    await callback.answer()


@router.message(RepairForm.namebike)
async def process_namebike(message: Message, state: FSMContext):
    """Сохраняет название механического велосипеда и запрашивает поломки."""
    await state.update_data(namebike=message.text)
    await state.set_state(RepairForm.breakdowns)
    await message.answer(
        "Введите поломки (можно несколько через запятую) и их стоимость через пробел (например: 'Порвана цепь 500, Прокол колеса 200'):"
    )


@router.message(RepairForm.breakdowns)
@router.message(EditRepairForm.breakdowns)
async def process_breakdowns_input(message: Message, state: FSMContext):
    """Обрабатывает ввод поломок для механического велосипеда."""
    text = message.text
    parsed_breakdowns, calculated_cost = parse_breakdowns_with_cost(text)

    await state.update_data(
        breakdowns=parsed_breakdowns, calculated_cost=calculated_cost
    )
    await state.set_state(RepairForm.cost)
    await message.answer(
        f"Предполагаемая стоимость ремонта: <b>{calculated_cost} руб.</b>\n"
        "Введите итоговую стоимость или примите предложенную:",
        reply_markup=confirm_total_cost_kb(calculated_cost),
    )


@router.callback_query(
    F.data.startswith("add_e_bike_problem:"), RepairForm.e_bike_breakdowns_select
)
async def add_e_bike_problem(callback: CallbackQuery, state: FSMContext):
    """Добавляет/удаляет стандартную поломку для электровелосипеда."""
    problem = callback.data.split(":")[1]
    user_data = await state.get_data()
    current_breakdowns = user_data.get("breakdowns", [])

    if problem in current_breakdowns:
        current_breakdowns.remove(problem)
    else:
        current_breakdowns.append(problem)

    await state.update_data(breakdowns=current_breakdowns)
    await callback.message.edit_reply_markup(
        reply_markup=e_bike_problems_inline(current_breakdowns)
    )
    await callback.answer()


@router.callback_query(
    F.data == "input_custom_breakdowns", RepairForm.e_bike_breakdowns_select
)
async def input_custom_breakdowns(callback: CallbackQuery, state: FSMContext):
    """Переключает на ручной ввод кастомных поломок для электровелосипеда."""
    await state.set_state(RepairForm.e_bike_breakdowns_custom)
    await callback.message.edit_text(
        "Введите свои поломки с ценой (например: 'Замена цепи 500').\n"
        "Чтобы пропустить, отправьте '-'."
    )
    await callback.answer()


@router.message(RepairForm.e_bike_breakdowns_custom)
async def process_e_bike_custom_breakdowns(message: Message, state: FSMContext):
    """Обрабатывает кастомные поломки и переходит к подтверждению цены."""
    text = message.text
    user_data = await state.get_data()
    selected_standard_breakdowns = user_data.get("breakdowns", [])

    custom_breakdowns_list, calculated_cost = [], 0
    if text != "-":
        custom_breakdowns_list, calculated_cost = parse_breakdowns_with_cost(text)

    final_breakdowns = selected_standard_breakdowns + custom_breakdowns_list
    await state.update_data(
        breakdowns=final_breakdowns, calculated_cost=calculated_cost
    )
    await state.set_state(RepairForm.cost)
    await message.answer(
        f"Предполагаемая стоимость: <b>{calculated_cost} руб.</b>\n"
        "Подтвердите или введите свою сумму.",
        reply_markup=confirm_total_cost_kb(calculated_cost),
    )


@router.callback_query(
    F.data == "finish_breakdowns_selection", RepairForm.e_bike_breakdowns_select
)
async def finish_e_bike_selection(callback: CallbackQuery, state: FSMContext):
    """Завершает выбор поломок для электровелосипеда и переходит к цене."""
    await state.set_state(RepairForm.cost)
    await callback.message.edit_text(
        "Выбор поломок завершен. Введите итоговую стоимость ремонта:",
        reply_markup=confirm_total_cost_kb(0),
    )
    await callback.answer()


@router.message(RepairForm.cost)
async def process_cost_input(message: Message, state: FSMContext):
    """Обрабатывает ручной ввод стоимости."""
    try:
        cost = int(message.text)
        await state.update_data(cost=cost)
        await state.set_state(RepairForm.notes)
        await message.answer(
            "Введите примечания к ремонту или пропустите:",
            reply_markup=skip_notes_inline_kb(),
        )
    except ValueError:
        await message.answer("Пожалуйста, введите числовое значение стоимости.")


@router.callback_query(F.data.startswith("confirm_cost:"), RepairForm.cost)
async def confirm_cost(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает подтверждение предложенной стоимости."""
    suggested_cost = int(callback.data.split(":")[1])
    await state.update_data(cost=suggested_cost)
    await state.set_state(RepairForm.notes)
    await callback.message.edit_text(
        "Введите примечания к ремонту или пропустите:",
        reply_markup=skip_notes_inline_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "enter_custom_cost", RepairForm.cost)
async def enter_custom_cost(callback: CallbackQuery, state: FSMContext):
    """Запрос на ввод кастомной стоимости."""
    await callback.message.edit_text("Хорошо, введите итоговую стоимость:")
    await callback.answer()


@router.message(RepairForm.notes)
async def process_notes(message: Message, state: FSMContext):
    """Сохраняет примечания и завершает создание ремонта."""
    await state.update_data(notes=message.text)
    await finalize_repair_creation(message, state)


@router.callback_query(F.data == "skip_notes", RepairForm.notes)
async def skip_notes(callback: CallbackQuery, state: FSMContext):
    """Пропускает ввод примечаний и завершает создание ремонта."""
    await state.update_data(notes="-")
    await finalize_repair_creation(callback.message, state)
    await callback.answer()


async def finalize_repair_creation(message: Message, state: FSMContext):
    """
    Собирает все данные, сохраняет ремонт и отправляет итоговую карточку.
    """
    user_data = await state.get_data()
    new_repair_id = storage.get_next_repair_id()

    user_data["id"] = new_repair_id
    user_data["date"] = datetime.now().strftime("%d.%m.%Y")

    # Установка значений по-умолчанию для необязательных полей
    user_data.setdefault("breakdowns", [])
    user_data.setdefault("cost", 0)
    user_data.setdefault("notes", "-")
    user_data.setdefault("namebike", "-")
    user_data.setdefault("repair_type", "unknown")  # Добавлено поле типа ремонта

    storage.add_repair(user_data)

    await message.answer(
        f"✅ Ремонт успешно добавлен!\n\n" + format_repair_details(user_data),
        reply_markup=detail_repair_inline(new_repair_id),
    )
    await state.clear()
