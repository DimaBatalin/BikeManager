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
        await callback.answer()
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
    elif field_name == "isMechanics":
        await state.set_state(EditRepairForm.is_mechanics)
        await callback.message.edit_text(
            f"Выберите новый тип велосипеда (текущий: {'Механический' if current_repair_data.get('isMechanics') else 'Электровелосипед'}):",
            reply_markup=edit_bike_type_inline(int(repair_id)),
        )
    elif field_name == "namebike":
        await state.set_state(EditRepairForm.namebike)
        await callback.message.edit_text(
            f"Введите новое название велосипеда (текущее: <code>{current_repair_data.get('namebike', '-') }</code>):"
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
        else:  # Если электровелосипед
            await state.set_state(EditRepairForm.e_bike_breakdowns_edit_select)
            
            # --- ИЗМЕНЕНИЕ 1: Сохраняем текущие поломки во временное состояние FSM ---
            current_breakdowns = current_repair_data.get("breakdowns", [])
            await state.update_data(
                current_edit_repair_id=repair_id, # Оставляем для совместимости, но лучше использовать repair_id_to_edit
                temp_breakdowns=current_breakdowns[:] # Сохраняем КОПИЮ в состояние
            )

            # --- ИЗМЕНЕНИЕ 2: Фильтруем для клавиатуры только стандартные поломки ---
            standard_breakdowns = [
                b for b in current_breakdowns if not search(r"\s+\d+$", b)
            ]
            
            await callback.message.edit_text(
                "Выберите стандартные поломки для электровелосипеда или введите свои (текущие поломки ниже):\n\n"
                + ", ".join(current_repair_data.get("breakdowns", []))
                + "\n\n",
                reply_markup=e_bike_problems_inline(standard_breakdowns),
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
    F.data.startswith("add_e_bike_problem:"),
    EditRepairForm.e_bike_breakdowns_edit_select,
)
async def edit_e_bike_problem_select(callback: CallbackQuery, state: FSMContext):
    # --- ИЗМЕНЕНИЕ 3: Полностью переработанная логика работы с состоянием FSM ---
    problem_text = callback.data.split(":")[1]
    user_data = await state.get_data()
    # Получаем список поломок из состояния FSM, а не из файла
    temp_breakdowns = user_data.get("temp_breakdowns", [])

    if problem_text in temp_breakdowns:
        temp_breakdowns.remove(problem_text)
    else:
        temp_breakdowns.append(problem_text)

    # Обновляем временный список в состоянии FSM
    await state.update_data(temp_breakdowns=temp_breakdowns)
    
    # Обновляем клавиатуру, показывая текущие выбранные (стандартные) поломки
    standard_breakdowns = [b for b in temp_breakdowns if not search(r"\s+\d+$", b)]
    await callback.message.edit_reply_markup(
        reply_markup=e_bike_problems_inline(standard_breakdowns)
    )
    await callback.answer()


@router.callback_query(
    F.data == "input_custom_breakdowns", EditRepairForm.e_bike_breakdowns_edit_select
)
async def edit_e_bike_input_custom_breakdowns(
    callback: CallbackQuery, state: FSMContext
):
    await state.set_state(EditRepairForm.e_bike_breakdowns_edit_custom)
    user_data = await state.get_data()
    # Получаем текущие поломки из FSM для отображения
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
    # --- ИЗМЕНЕНИЕ 4: Правильно комбинируем стандартные и кастомные поломки и переходим к подтверждению цены ---
    text = message.text
    user_data = await state.get_data()
    repair_id = user_data.get("repair_id_to_edit")
    temp_breakdowns = user_data.get("temp_breakdowns", [])

    if repair_id is None:
        await message.answer("Ошибка: ID ремонта для редактирования не найден.", reply_markup=main_reply_kb())
        await state.clear()
        return

    # 1. Берем стандартные поломки (без цены) из временного списка
    standard_selections = [
        b for b in temp_breakdowns if not search(r"\s+\d+$", b)
    ]
    
    # 2. Парсим новые кастомные поломки
    custom_breakdowns_list, _ = [], 0
    if text != "-":
        custom_breakdowns_list, _ = parse_breakdowns_with_cost(text)

    # 3. Соединяем их
    final_breakdowns = standard_selections + custom_breakdowns_list
    
    # 4. Сохраняем итоговый список поломок в файл
    storage.update_repair_field(repair_id, "breakdowns", final_breakdowns)

    # 5. Пересчитываем общую стоимость и предлагаем ее подтвердить
    total_cost_from_breakdowns = 0
    for bd in final_breakdowns:
        match = search(r"\s+(\d+)$", bd)
        if match:
            total_cost_from_breakdowns += int(match.group(1))

    await state.update_data(calculated_cost=total_cost_from_breakdowns)
    await state.set_state(EditRepairForm.cost) # Переходим к состоянию подтверждения цены
    
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
    # --- ИЗМЕНЕНИЕ 5: Логика завершения выбора теперь тоже переходит к подтверждению цены ---
    user_data = await state.get_data()
    repair_id = user_data.get("repair_id_to_edit")
    final_breakdowns = user_data.get("temp_breakdowns", []) # Берем итоговый список из состояния

    if repair_id is None:
        await callback.message.answer("Ошибка: ID ремонта для редактирования не найден.", reply_markup=main_reply_kb())
        await state.clear()
        return

    # Сохраняем итоговый список поломок в файл
    storage.update_repair_field(repair_id, "breakdowns", final_breakdowns)
    
    # Пересчитываем общую стоимость
    total_cost_from_breakdowns = 0
    for bd in final_breakdowns:
        match = search(r"\s+(\d+)$", bd)
        if match:
            total_cost_from_breakdowns += int(match.group(1))
            
    # Переходим к состоянию подтверждения цены
    await state.update_data(calculated_cost=total_cost_from_breakdowns)
    await state.set_state(EditRepairForm.cost)

    await callback.message.edit_text(
        f"Выбор поломок завершен. Предполагаемая стоимость: <b>{total_cost_from_breakdowns} руб.</b>\n"
        "Введите итоговую стоимость или нажмите 'Принять'.",
        reply_markup=confirm_total_cost_kb(total_cost_from_breakdowns),
    )
    await callback.answer()


# Остальной код файла edit_repairs.py остается без изменений
# (обработчики update_fio, update_contact, update_bike_type и т.д.)
# ... (весь оставшийся код файла) ...
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


@router.callback_query(F.data.startswith("set_type:"), EditRepairForm.is_mechanics)
@router.callback_query(
    F.data.startswith("set_bike_type:"), EditRepairForm.is_mechanics
)  # Добавлено для совместимости
async def update_bike_type(callback: CallbackQuery, state: FSMContext):
    is_mechanics = None
    if callback.data.startswith("set_type:"):
        is_mechanics = callback.data.split(":")[1] == "True"
    elif callback.data.startswith("set_bike_type:"):
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

    if not is_mechanics:  # Если изменили на электровелосипед
        storage.update_repair_field(
            repair_id, "namebike", "Электровелосипед"
        )  # Автоматически установить имя

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