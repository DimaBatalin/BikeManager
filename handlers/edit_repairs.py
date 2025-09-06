from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import services.storage as storage
from utils.keyboard import (
    main_reply_kb,
    detail_repair_inline,
    edit_repair_options_inline,
    e_bike_problems_inline,
    edit_bike_type_inline,
    confirm_total_cost_kb,
    edit_repair_type_keyboard,
)
from utils.formatter import format_repair_details, parse_breakdowns_with_cost
from fsm_states import EditRepairForm

from re import search
from datetime import datetime

router = Router()


def register_handlers(dp):
    dp.include_router(router)


@router.callback_query(F.data.startswith("edit_repair:"))
async def edit_repair(callback: CallbackQuery, state: FSMContext):
    repair_id = int(callback.data.split(":")[1])
    repair_data = storage.get_active_repair_data_by_id(int(repair_id))
    if not repair_data:
        await callback.message.answer("Ремонт не найден.")
        await callback.answer()
        return

    await state.set_state(EditRepairForm.select_field)
    await state.update_data(repair_id_to_edit=repair_id)
    await callback.message.edit_text(
        f"Выберите, какое поле ремонта ID: {repair_id} хотите отредактировать:",
        reply_markup=edit_repair_options_inline(repair_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("field:"), EditRepairForm.select_field)
async def select_field_to_edit(callback: CallbackQuery, state: FSMContext):
    _, field_name, repair_id = callback.data.split(":")
    await state.update_data(field_name=field_name)

    current_repair_data = storage.get_active_repair_data_by_id(int(repair_id))
    if not current_repair_data:
        await callback.message.answer("Ремонт не найден.")
        await state.clear()
        return

    if field_name == "FIO":
        await state.set_state(EditRepairForm.fio)
        await callback.message.edit_text(
            f"Введите новое ФИО клиента (текущее: <code>{current_repair_data.get('FIO')}</code>):"
        )
    elif field_name == "contact":
        await state.set_state(EditRepairForm.contact)
        await callback.message.edit_text(
            f"Введите новый контакт (текущий: <code>{current_repair_data.get('contact')}</code>):"
        )
    elif field_name == "repair_type":
        await state.set_state(EditRepairForm.repair_type)
        current_source = current_repair_data.get("repair_type", "не указан")
        sources_dict = storage.get_repair_sources()
        source_name = sources_dict.get(current_source, current_source)
        message_text = (
            f"Текущий источник: <b>{source_name}</b>\n\nВыберите новый источник:"
        )
        await callback.message.edit_text(
            message_text, reply_markup=edit_repair_type_keyboard(repair_id)
        )
    elif field_name == "isMechanics":
        await state.set_state(EditRepairForm.is_mechanics)
        await callback.message.edit_text(
            f"Выберите новый тип велосипеда (текущий: {'Механический' if current_repair_data.get('isMechanics') else 'Электровелосипед'}):",
            reply_markup=edit_bike_type_inline(int(repair_id)),
        )
    elif field_name == "namebike":
        await state.set_state(EditRepairForm.namebike)
        await callback.message.edit_text(
            f"Введите новое название велосипеда (текущее: <code>{current_repair_data.get('namebike', '-')}</code>):"
        )
    elif field_name == "breakdowns":
        is_mechanics = current_repair_data.get("isMechanics", True)
        if is_mechanics:
            await state.set_state(EditRepairForm.breakdowns)
            current_breakdowns_str = ", ".join(
                current_repair_data.get("breakdowns", [])
            )
            await callback.message.edit_text(
                f"Введите новые поломки (можно несколько через запятую) и их стоимость через пробел "
                f"(например: 'Порвана цепь 500, Прокол колеса 200').\n"
                f"Текущие поломки: <code>{current_breakdowns_str if current_breakdowns_str else '-'}</code>:"
            )
        else:  # Электровелосипед
            await state.set_state(EditRepairForm.e_bike_breakdowns_edit_select)
            current_breakdowns = current_repair_data.get("breakdowns", [])

            # Приводим к базовым названиям (чтобы галочки работали и для "с ценой")
            base_breakdowns = []
            for bd in current_breakdowns:
                base = bd.rsplit(" ", 1)[0] if search(r"\s+\d+$", bd) else bd
                base_breakdowns.append(base)

            await state.update_data(
                temp_breakdowns=current_breakdowns[:],
            )

            await callback.message.edit_text(
                "Выберите стандартные поломки для электровелосипеда или введите свои (текущие поломки ниже):\n\n"
                + ", ".join(current_breakdowns)
                + "\n\n",
                reply_markup=e_bike_problems_inline(base_breakdowns),
            )

    elif field_name == "cost":
        await state.set_state(EditRepairForm.cost)
        current_cost = current_repair_data.get("cost", 0)
        await callback.message.edit_text(
            f"Введите новую стоимость (текущая: <code>{current_cost}</code> руб.):"
        )
    elif field_name == "notes":
        await state.set_state(EditRepairForm.notes)
        await callback.message.edit_text(
            f"Введите новые примечания (текущие: <code>{current_repair_data.get('notes', '-')}</code>):"
        )
    elif field_name == "date":
        await state.set_state(EditRepairForm.date)
        await callback.message.edit_text(
            f"Введите новую дату в формате ДД.ММ.ГГГГ (текущая: <code>{current_repair_data.get('date', '-')}</code>):"
        )
    await callback.answer()


@router.callback_query(
    F.data.startswith("set_repair_source:"), EditRepairForm.repair_type
)
async def set_repair_source(callback: CallbackQuery, state: FSMContext):
    data_parts = callback.data.split(":")
    source_key = data_parts[1]
    repair_id = int(data_parts[2])

    storage.update_repair_field(repair_id, "repair_type", source_key)
    repair = storage.get_active_repair_data_by_id(repair_id)
    sources_dict = storage.get_repair_sources()
    source_name = sources_dict.get(source_key, source_key)

    await callback.message.edit_text(
        f"✅ Источник ремонта обновлен на: <b>{source_name}</b>\n\n"
        + format_repair_details(repair),
        reply_markup=detail_repair_inline(repair_id),
    )
    await state.clear()


@router.callback_query(
    F.data.startswith("add_e_bike_problem:"),
    EditRepairForm.e_bike_breakdowns_edit_select,
)
async def edit_e_bike_problem_select(callback: CallbackQuery, state: FSMContext):
    problem_text = callback.data.split(":")[1]
    user_data = await state.get_data()
    temp_breakdowns = user_data.get("temp_breakdowns", [])

    is_present = any(
        bd == problem_text or bd.startswith(problem_text + " ")
        for bd in temp_breakdowns
    )

    if is_present:
        temp_breakdowns = [
            bd for bd in temp_breakdowns
            if not (bd == problem_text or bd.startswith(problem_text + " "))
        ]
    else:
        temp_breakdowns.append(problem_text)
    
    await state.update_data(temp_breakdowns=temp_breakdowns)

    base_selected = []
    for bd in temp_breakdowns:
        base = bd.rsplit(" ", 1)[0] if search(r"\s+\d+$", bd) else bd
        base_selected.append(base)

    new_markup = e_bike_problems_inline(base_selected)

    if callback.message.reply_markup != new_markup:
        await callback.message.edit_reply_markup(reply_markup=new_markup)
    
    await callback.answer()



@router.callback_query(
    F.data == "input_custom_breakdowns", EditRepairForm.e_bike_breakdowns_edit_select
)
async def edit_e_bike_input_custom_breakdowns(
    callback: CallbackQuery, state: FSMContext
):
    await state.set_state(EditRepairForm.e_bike_breakdowns_edit_custom)
    user_data = await state.get_data()
    temp_breakdowns = user_data.get("temp_breakdowns", [])
    current_breakdowns_str = ", ".join(temp_breakdowns)

    await callback.message.edit_text(
        "Введите <i>только кастомные</i> поломки (с ценой через пробел, через запятую), "
        "которые вы хотите добавить. Стандартные поломки, выбранные галочками, сохранятся.\n"
        "Чтобы пропустить, отправьте '-'.\n"
        f"\nТекущий полный список: <code>{current_breakdowns_str}</code>"
    )
    await callback.answer()


@router.message(EditRepairForm.e_bike_breakdowns_edit_custom)
async def process_edit_e_bike_custom_breakdowns(message: Message, state: FSMContext):
    text = message.text
    user_data = await state.get_data()
    repair_id = user_data.get("repair_id_to_edit")

    if repair_id is None:
        await message.answer(
            "Ошибка: ID ремонта для редактирования не найден.",
            reply_markup=main_reply_kb(),
        )
        await state.clear()
        return

    if text == "-":
        # Пользователь решил оставить только стандартные (галочками)
        final_breakdowns = user_data.get("temp_breakdowns", [])
    else:
        # Полностью заменяем список (как у механических)
        final_breakdowns, _ = parse_breakdowns_with_cost(text)

    # --- Убираем дубли и объединяем стандартную и ту же поломку с ценой ---
    normalized = {}
    for bd in final_breakdowns:
        base = bd.rsplit(" ", 1)[0] if search(r"\s+\d+$", bd) else bd
        normalized[base] = bd  # если есть цена — перезапишет «голую» поломку

    final_breakdowns = list(normalized.values())

    # Сохраняем
    storage.update_repair_field(repair_id, "breakdowns", final_breakdowns)

    # Считаем итоговую стоимость
    total_cost_from_breakdowns = 0
    for bd in final_breakdowns:
        match = search(r"\s+(\d+)$", bd)
        if match:
            total_cost_from_breakdowns += int(match.group(1))

    await state.update_data(calculated_cost=total_cost_from_breakdowns)
    await state.set_state(EditRepairForm.cost)

    await message.answer(
        f"Поломки обновлены. Предполагаемая стоимость: <b>{total_cost_from_breakdowns} руб.</b>\n"
        "Введите итоговую стоимость или нажмите 'Принять', чтобы использовать предложенную сумму.",
        reply_markup=confirm_total_cost_kb(total_cost_from_breakdowns),
    )


@router.callback_query(
    F.data == "finish_breakdowns_selection",
    EditRepairForm.e_bike_breakdowns_edit_select,
)
async def finish_edit_e_bike_selection(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    repair_id = user_data.get("repair_id_to_edit")
    temp_breakdowns = user_data.get("temp_breakdowns", [])

    if repair_id is None:
        await callback.message.answer(
            "Ошибка: ID ремонта для редактирования не найден.",
            reply_markup=main_reply_kb(),
        )
        await state.clear()
        return

    # --- Убираем дубли и объединяем стандартную и ту же поломку с ценой ---
    normalized = {}
    for bd in temp_breakdowns:
        base = bd.rsplit(" ", 1)[0] if search(r"\s+\d+$", bd) else bd
        normalized[base] = bd

    final_breakdowns = list(normalized.values())

    storage.update_repair_field(repair_id, "breakdowns", final_breakdowns)

    total_cost_from_breakdowns = 0
    for bd in final_breakdowns:
        match = search(r"\s+(\d+)$", bd)
        if match:
            total_cost_from_breakdowns += int(match.group(1))

    await state.update_data(calculated_cost=total_cost_from_breakdowns)
    await state.set_state(EditRepairForm.cost)

    await callback.message.edit_text(
        f"Выбор поломок завершен. Предполагаемая стоимость: <b>{total_cost_from_breakdowns} руб.</b>\n"
        "Введите итоговую стоимость или нажмите 'Принять'.",
        reply_markup=confirm_total_cost_kb(total_cost_from_breakdowns),
    )
    await callback.answer()


@router.message(EditRepairForm.breakdowns)
async def process_edit_mechanical_breakdowns(message: Message, state: FSMContext):
    """Обрабатывает ввод поломок для механического велосипеда при редактировании."""
    text = message.text
    parsed_breakdowns, calculated_cost = parse_breakdowns_with_cost(text)

    user_data = await state.get_data()
    repair_id = user_data.get("repair_id_to_edit")
    storage.update_repair_field(repair_id, "breakdowns", parsed_breakdowns)

    await state.update_data(calculated_cost=calculated_cost)
    await state.set_state(EditRepairForm.cost)
    await message.answer(
        f"Поломки обновлены. Предполагаемая стоимость: <b>{calculated_cost} руб.</b>\n"
        "Введите итоговую стоимость или нажмите 'Принять', чтобы использовать предложенную сумму.",
        reply_markup=confirm_total_cost_kb(calculated_cost),
    )


@router.callback_query(F.data.startswith("confirm_cost:"), EditRepairForm.cost)
async def process_confirm_cost_edit(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает подтверждение предложенной стоимости при редактировании."""
    try:
        cost = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("Ошибка в данных стоимости.", show_alert=True)
        return

    user_data = await state.get_data()
    repair_id = user_data.get("repair_id_to_edit")
    if repair_id is None:
        await callback.message.answer(
            "Ошибка: ID ремонта не найден.", reply_markup=main_reply_kb()
        )
        await state.clear()
        return

    storage.update_repair_field(repair_id, "cost", cost)
    repair = storage.get_active_repair_data_by_id(int(repair_id))

    await callback.message.edit_text(
        f"✅ Стоимость обновлена для ремонта ID: {repair_id}.\n\n"
        + format_repair_details(repair),
        reply_markup=detail_repair_inline(repair_id),
    )
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "enter_custom_cost", EditRepairForm.cost)
async def process_enter_custom_cost_edit(callback: CallbackQuery, state: FSMContext):
    """Запрос на ввод кастомной стоимости при редактировании."""
    await callback.message.edit_text("Хорошо, введите итоговую стоимость:")
    await callback.answer()


@router.message(EditRepairForm.cost)
async def process_cost_input_edit(message: Message, state: FSMContext):
    """Обрабатывает ручной ввод стоимости при редактировании."""
    try:
        cost = int(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введите числовое значение стоимости.")
        return

    user_data = await state.get_data()
    repair_id = user_data.get("repair_id_to_edit")
    if repair_id is None:
        await message.answer(
            "Ошибка: ID ремонта не найден.", reply_markup=main_reply_kb()
        )
        await state.clear()
        return

    storage.update_repair_field(repair_id, "cost", cost)
    repair = storage.get_active_repair_data_by_id(int(repair_id))

    await message.answer(
        f"✅ Стоимость обновлена для ремонта ID: {repair_id}.\n\n"
        + format_repair_details(repair),
        reply_markup=detail_repair_inline(repair_id),
    )
    await state.clear()


# ---- КОНЕЦ НОВОГО БЛОКА ----


@router.message(EditRepairForm.fio)
async def update_fio(message: Message, state: FSMContext):
    user_data = await state.get_data()
    repair_id = user_data.get("repair_id_to_edit")
    if repair_id is None:
        await message.answer(
            "Ошибка: ID ремонта не найден.", reply_markup=main_reply_kb()
        )
        await state.clear()
        return

    storage.update_repair_field(repair_id, "FIO", message.text)
    repair = storage.get_active_repair_data_by_id(int(repair_id))
    await message.answer(
        f"✅ ФИО обновлено для ремонта ID: {repair_id}.\n\n"
        + format_repair_details(repair),
        reply_markup=detail_repair_inline(repair_id),
    )
    await state.clear()


@router.message(EditRepairForm.contact)
async def update_contact(message: Message, state: FSMContext):
    user_data = await state.get_data()
    repair_id = user_data.get("repair_id_to_edit")
    if repair_id is None:
        await message.answer(
            "Ошибка: ID ремонта не найден.", reply_markup=main_reply_kb()
        )
        await state.clear()
        return

    storage.update_repair_field(repair_id, "contact", message.text)
    repair = storage.get_active_repair_data_by_id(int(repair_id))
    await message.answer(
        f"✅ Контакт обновлен для ремонта ID: {repair_id}.\n\n"
        + format_repair_details(repair),
        reply_markup=detail_repair_inline(repair_id),
    )
    await state.clear()


@router.callback_query(F.data.startswith("set_bike_type:"), EditRepairForm.is_mechanics)
async def update_bike_type(callback: CallbackQuery, state: FSMContext):
    bike_type_str = callback.data.split(":")[1]
    is_mechanics = bike_type_str == "mechanics"

    if is_mechanics is None:
        await callback.answer("Неизвестный тип велосипеда.", show_alert=True)
        return

    user_data = await state.get_data()
    repair_id = user_data.get("repair_id_to_edit")
    if repair_id is None:
        await callback.message.answer(
            "Ошибка: ID ремонта не найден.", reply_markup=main_reply_kb()
        )
        await state.clear()
        return

    storage.update_repair_field(repair_id, "isMechanics", is_mechanics)
    if not is_mechanics:
        storage.update_repair_field(repair_id, "namebike", "Электровелосипед")

    repair = storage.get_active_repair_data_by_id(int(repair_id))
    await callback.message.edit_text(
        f"✅ Тип велосипеда обновлен для ремонта ID: {repair_id}.\n\n"
        + format_repair_details(repair),
        reply_markup=detail_repair_inline(repair_id),
    )
    await state.clear()
    await callback.answer()


@router.message(EditRepairForm.namebike)
async def update_namebike(message: Message, state: FSMContext):
    user_data = await state.get_data()
    repair_id = user_data.get("repair_id_to_edit")
    if repair_id is None:
        await message.answer(
            "Ошибка: ID ремонта не найден.", reply_markup=main_reply_kb()
        )
        await state.clear()
        return

    storage.update_repair_field(repair_id, "namebike", message.text)
    repair = storage.get_active_repair_data_by_id(int(repair_id))
    await message.answer(
        f"✅ Название велосипеда обновлено для ремонта ID: {repair_id}.\n\n"
        + format_repair_details(repair),
        reply_markup=detail_repair_inline(repair_id),
    )
    await state.clear()


@router.message(EditRepairForm.notes)
async def update_notes(message: Message, state: FSMContext):
    user_data = await state.get_data()
    repair_id = user_data.get("repair_id_to_edit")
    if repair_id is None:
        await message.answer(
            "Ошибка: ID ремонта не найден.", reply_markup=main_reply_kb()
        )
        await state.clear()
        return

    storage.update_repair_field(repair_id, "notes", message.text)
    repair = storage.get_active_repair_data_by_id(int(repair_id))
    await message.answer(
        f"✅ Примечания обновлены для ремонта ID: {repair_id}.\n\n"
        + format_repair_details(repair),
        reply_markup=detail_repair_inline(repair_id),
    )
    await state.clear()


@router.message(EditRepairForm.date)
async def update_date(message: Message, state: FSMContext):
    user_data = await state.get_data()
    repair_id = user_data.get("repair_id_to_edit")
    if repair_id is None:
        await message.answer(
            "Ошибка: ID ремонта не найден.", reply_markup=main_reply_kb()
        )
        await state.clear()
        return

    try:
        datetime.strptime(message.text, "%d.%m.%Y")
    except ValueError:
        await message.answer(
            "Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ."
        )
        return

    storage.update_repair_field(repair_id, "date", message.text)
    repair = storage.get_active_repair_data_by_id(int(repair_id))
    await message.answer(
        f"✅ Дата обновлена для ремонта ID: {repair_id}.\n\n"
        + format_repair_details(repair),
        reply_markup=detail_repair_inline(repair_id),
    )
    await state.clear()


@router.callback_query(F.data.startswith("cancel_edit:"))
async def cancel_edit(callback: CallbackQuery, state: FSMContext):
    repair_id = int(callback.data.split(":")[1])
    await state.clear()
    repair_data = storage.get_active_repair_data_by_id(int(repair_id))
    if repair_data:
        await callback.message.edit_text(
            f"Редактирование отменено.\n\n" + format_repair_details(repair_data),
            reply_markup=detail_repair_inline(repair_id),
        )
    else:
        await callback.message.edit_text(
            "Редактирование отменено.", reply_markup=main_reply_kb()
        )
    await callback.answer()


@router.callback_query(F.data.startswith("close_repair:"))
async def close_repair(callback: CallbackQuery, state: FSMContext):
    if callback.message and callback.data:
        try:
            repair_id = int(callback.data.split(":")[1])
        except ValueError:
            await callback.answer("Некорректный ID ремонта.", show_alert=True)
            return

        if storage.archive_repair_by_id(repair_id):
            await callback.message.answer(
                f"Ремонт ID: {repair_id} успешно закрыт и перемещен в архив.",
                reply_markup=main_reply_kb(),
            )
        else:
            await callback.message.answer(
                "Не удалось закрыть ремонт. Возможно, он уже в архиве или не существует."
            )
        await callback.answer()
    else:
        await callback.answer("Произошла ошибка при закрытии ремонта.", show_alert=True)
