# active_repairs.py
from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import services.storage as storage
from utils.keyboard import (  # Изменено с keyboards на utils.keyboard
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

import re
from datetime import datetime

router = Router()


def register_handlers(dp):
    dp.include_router(router)


# --- FSM States --- (без изменений)
class RepairForm(StatesGroup):
    fio = State()
    contact = State()
    bike_type = State()
    namebike = State()
    breakdowns = State()
    e_bike_breakdowns_select = State()
    e_bike_breakdowns_custom = State()
    cost = State()
    notes = State()


class EditRepairForm(StatesGroup):
    select_field = State()
    fio = State()
    contact = State()
    bike_type = State()
    namebike = State()
    breakdowns = State()
    e_bike_breakdowns_edit_select = State()
    e_bike_breakdowns_edit_custom = State()
    cost = State()
    notes = State()
    date = State()
    is_mechanics = State()


def parse_breakdowns_with_cost(text: str) -> tuple[list[str], int]:
    breakdowns_list = []
    total_cost = 0
    parts = [part.strip() for part in text.split(",")]
    for part in parts:
        match = re.search(r"\s+(\d+)$", part)
        if match:
            cost = int(match.group(1))
            # breakdown_text = part[: match.start()].strip()
            breakdowns_list.append(part)
            total_cost += cost
        else:
            breakdowns_list.append(part)
    return breakdowns_list, total_cost


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


# --- ХЕНДЛЕР ДЛЯ КНОПКИ "НАЗАД В МЕНЮ" ---
@router.callback_query(F.data == "back_to_main_menu")
async def back_to_main_menu_from_active_list(callback: CallbackQuery):
    await callback.message.edit_text("Вы в главном меню.", reply_markup=main_reply_kb())
    await callback.answer()


# --- ХЕНДЛЕРЫ ДОБАВЛЕНИЯ НОВОГО РЕМОНТА ---


# *ОБНОВЛЕНО*: Добавлен обработчик для callback_data="new_repair" и "new_repair_from_empty"
@router.message(F.text == "Добавить ремонт")
@router.message(Command("add_repair"))
@router.callback_query(
    F.data == "new_repair"
)  # Обработчик для кнопки из active_repairs_inline
@router.callback_query(
    F.data == "new_repair_from_empty"
)  # Обработчик для кнопки, если ремонтов нет
async def start_add_repair(
    update: types.Union[Message, CallbackQuery], state: FSMContext
):
    # Определяем, был ли это Message или CallbackQuery
    if isinstance(update, Message):
        await update.answer("Введите ФИО клиента:")
    elif isinstance(update, CallbackQuery):
        await update.message.edit_text("Введите ФИО клиента:")
        await update.answer()  # Не забудьте ответить на callback

    await state.set_state(RepairForm.fio)


@router.message(RepairForm.fio)
async def process_fio(message: Message, state: FSMContext):
    await state.update_data(FIO=message.text)
    await state.set_state(RepairForm.contact)
    await message.answer("Введите контактный телефон клиента:")


@router.message(RepairForm.contact)
async def process_contact(message: Message, state: FSMContext):
    await state.update_data(contact=message.text)
    await state.set_state(RepairForm.bike_type)
    # Здесь тоже нужно изменить на select_bike_type_inline() без аргумента,
    # так как вы поменяли ее в keyboard.py на без аргументов.
    await message.answer(
        "Выберите тип велосипеда:", reply_markup=select_bike_type_inline()
    )


@router.callback_query(F.data.startswith("set_type:"), RepairForm.bike_type)
@router.callback_query(F.data.startswith("set_bike_type:"), RepairForm.bike_type)
async def process_bike_type(callback: CallbackQuery, state: FSMContext):
    is_mechanics = None
    if callback.data.startswith("set_type:"):
        is_mechanics = callback.data.split(":")[1] == "True"
    elif callback.data.startswith("set_bike_type:"):
        bike_type_str = callback.data.split(":")[1]
        is_mechanics = bike_type_str == "mechanics"

    if is_mechanics is None:
        await callback.answer("Неизвестный тип велосипеда.", show_alert=True)
        return

    await state.update_data(isMechanics=is_mechanics)

    if not is_mechanics:  # Если это электровелосипед
        await state.update_data(namebike="Электровелосипед")
        await state.set_state(RepairForm.e_bike_breakdowns_select)
        await state.update_data(
            breakdowns=[]
        )  # Инициализируем breakdowns пустым списком
        await callback.message.edit_text(
            "Тип велосипеда установлен как **Электровелосипед** (имя по умолчанию).\n"
            "Выберите стандартные поломки или введите свои:",
            reply_markup=e_bike_problems_inline([]),
        )
    else:  # Если это механический велосипед
        await state.set_state(RepairForm.namebike)
        await callback.message.edit_text("Введите название велосипеда:")

    await callback.answer()


@router.message(RepairForm.namebike)
async def process_namebike(message: Message, state: FSMContext):
    await state.update_data(namebike=message.text)
    user_data = await state.get_data()

    if user_data.get("isMechanics"):
        await state.set_state(RepairForm.breakdowns)
        await message.answer(
            "Введите поломки (можно несколько через запятую) и их стоимость через пробел (например: 'Порвана цепь 500, Прокол колеса 200'):"
        )
    else:
        await state.set_state(RepairForm.e_bike_breakdowns_select)
        await state.update_data(breakdowns_selected=[])
        await message.answer(
            "Выберите стандартные поломки для электровелосипеда или введите свои:",
            reply_markup=e_bike_problems_inline([]),
        )


@router.message(RepairForm.breakdowns)
@router.message(EditRepairForm.breakdowns)
async def process_breakdowns_input(message: Message, state: FSMContext):
    text = message.text
    parsed_breakdowns, calculated_cost = parse_breakdowns_with_cost(text)

    current_state = await state.get_state()
    user_data = await state.get_data()

    if current_state == RepairForm.breakdowns.state:
        await state.update_data(
            breakdowns=parsed_breakdowns, calculated_cost=calculated_cost
        )
        await state.set_state(RepairForm.cost)
    elif current_state == EditRepairForm.breakdowns.state:
        repair_id = user_data.get("repair_id_to_edit")
        if repair_id is None:
            await message.answer(
                "Ошибка: ID ремонта для редактирования не найден.",
                reply_markup=main_reply_kb(),
            )
            await state.clear()
            return

        storage.update_repair_field(repair_id, "breakdowns", parsed_breakdowns)
        storage.update_repair_field(
            repair_id, "cost", calculated_cost
        )  # Обновляем и общую стоимость

        repair = storage.get_active_repair_data_by_id(int(repair_id))
        if repair:
            await message.answer(
                f"✅ Поломки и стоимость обновлены для ремонта ID: {repair_id}.\n\n"
                + format_repair_details(repair),
                reply_markup=detail_repair_inline(repair_id),
            )
        else:
            await message.answer(
                "✅ Поломки и стоимость обновлены.", reply_markup=main_reply_kb()
            )

        await state.clear()
        return

    await message.answer(
        f"Предполагаемая стоимость ремонта по поломкам: <b>{calculated_cost} руб.</b>\n"
        "Введите итоговую стоимость или нажмите 'Принять', чтобы использовать предложенную сумму.",
        reply_markup=confirm_total_cost_kb(calculated_cost),
    )


@router.callback_query(
    F.data.startswith("add_e_bike_problem:"), RepairForm.e_bike_breakdowns_select
)
async def add_e_bike_problem(callback: CallbackQuery, state: FSMContext):
    problem = callback.data.split(":")[1]
    user_data = await state.get_data()
    current_breakdowns = user_data.get("breakdowns", [])  # Получаем текущие поломки

    if problem in current_breakdowns:
        current_breakdowns.remove(problem)
    else:
        current_breakdowns.append(problem)

    await state.update_data(
        breakdowns=current_breakdowns
    )  # Обновляем breakdowns напрямую

    await callback.message.edit_reply_markup(
        reply_markup=e_bike_problems_inline(current_breakdowns)
    )
    await callback.answer()


@router.callback_query(
    F.data == "input_custom_breakdowns", RepairForm.e_bike_breakdowns_select
)
async def input_custom_breakdowns(callback: CallbackQuery, state: FSMContext):
    await state.set_state(RepairForm.e_bike_breakdowns_custom)
    await callback.message.edit_text(
        "Введите свои поломки (можно несколько через запятую) и их стоимость через пробел "
        "(например: 'Замена цепи 500, Настройка тормозов 300').\n"
        "Чтобы пропустить, отправьте '-'."
    )
    await callback.answer()


@router.message(RepairForm.e_bike_breakdowns_custom)
async def process_e_bike_custom_breakdowns(message: Message, state: FSMContext):
    text = message.text
    user_data = await state.get_data()
    selected_standard_breakdowns = user_data.get(
        "breakdowns", []
    )  # Теперь берем из 'breakdowns'

    custom_breakdowns_list, calculated_cost = [], 0

    if text != "-":
        custom_breakdowns_list, calculated_cost = parse_breakdowns_with_cost(text)

    final_breakdowns = selected_standard_breakdowns + custom_breakdowns_list

    await state.update_data(
        breakdowns=final_breakdowns, calculated_cost=calculated_cost
    )
    await state.set_state(RepairForm.cost)

    await message.answer(
        f"Предполагаемая стоимость ремонта по введенным поломкам: <b>{calculated_cost} руб.</b>\n"
        "Введите итоговую стоимость или нажмите 'Принять', чтобы использовать предложенную сумму.",
        reply_markup=confirm_total_cost_kb(calculated_cost),
    )


@router.callback_query(
    F.data == "finish_breakdowns_selection", RepairForm.e_bike_breakdowns_select
)
async def finish_e_bike_selection(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    final_breakdowns = user_data.get("breakdowns", [])  # Теперь берем из 'breakdowns'

    # Расчитываем стоимость из финальных поломок (если они содержат цену)
    total_cost_from_breakdowns = 0
    for bd in final_breakdowns:
        match = re.search(r"\s+(\d+)$", bd)
        if match:
            total_cost_from_breakdowns += int(match.group(1))

    await state.update_data(
        breakdowns=final_breakdowns,
        calculated_cost=total_cost_from_breakdowns,  # Обновляем calculated_cost
    )
    await state.set_state(RepairForm.cost)

    await callback.message.edit_text(
        f"Вы завершили выбор поломок. Предполагаемая стоимость: <b>{total_cost_from_breakdowns} руб.</b>\n"
        "Введите итоговую стоимость ремонта:",
        reply_markup=confirm_total_cost_kb(
            total_cost_from_breakdowns
        ),  # Предлагаем сумму
    )
    await callback.answer()


@router.message(RepairForm.cost)
@router.message(EditRepairForm.cost)
async def process_cost_input(message: Message, state: FSMContext):
    try:
        cost = int(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введите числовое значение стоимости.")
        return

    user_data = await state.get_data()
    current_state = await state.get_state()

    if current_state == RepairForm.cost.state:
        await state.update_data(cost=cost)
        await state.set_state(RepairForm.notes)
        await message.answer(
            "Введите примечания к ремонту или нажмите 'Без примечаний':",
            reply_markup=skip_notes_inline_kb(),
        )
    elif current_state == EditRepairForm.cost.state:
        repair_id = user_data.get("repair_id_to_edit")
        if repair_id is None:
            await message.answer(
                "Ошибка: ID ремонта для редактирования не найден.",
                reply_markup=main_reply_kb(),
            )
            await state.clear()
            return

        storage.update_repair_field(repair_id, "cost", cost)
        repair = storage.get_active_repair_data_by_id(int(repair_id))
        if repair:
            await message.answer(
                f"✅ Стоимость обновлена для ремонта ID: {repair_id}.\n\n"
                + format_repair_details(repair),
                reply_markup=detail_repair_inline(repair_id),
            )
        else:
            await message.answer(
                "✅ Стоимость обновлена.", reply_markup=main_reply_kb()
            )

        await state.clear()


@router.callback_query(F.data.startswith("confirm_cost:"), RepairForm.cost)
@router.callback_query(F.data.startswith("confirm_cost:"), EditRepairForm.cost)
async def confirm_cost(callback: CallbackQuery, state: FSMContext):
    suggested_cost = int(callback.data.split(":")[1])

    user_data = await state.get_data()
    current_state = await state.get_state()

    if current_state == RepairForm.cost.state:
        await state.update_data(cost=suggested_cost)
        await state.set_state(RepairForm.notes)
        await callback.message.edit_text(
            "Введите примечания к ремонту или нажмите 'Без примечаний':",
            reply_markup=skip_notes_inline_kb(),
        )
    elif current_state == EditRepairForm.cost.state:
        repair_id = user_data.get("repair_id_to_edit")
        if repair_id is None:
            await callback.message.answer(
                "Ошибка: ID ремонта для редактирования не найден.",
                reply_markup=main_reply_kb(),
            )
            await state.clear()
            return

        storage.update_repair_field(repair_id, "cost", suggested_cost)
        repair = storage.get_active_repair_data_by_id(int(repair_id))
        if repair:
            await callback.message.edit_text(
                f"✅ Стоимость обновлена для ремонта ID: {repair_id}.\n\n"
                + format_repair_details(repair),
                reply_markup=detail_repair_inline(repair_id),
            )
        else:
            await callback.message.answer(
                "✅ Стоимость обновлена.", reply_markup=main_reply_kb()
            )

        await state.clear()

    await callback.answer()


@router.callback_query(F.data == "enter_custom_cost", RepairForm.cost)
@router.callback_query(F.data == "enter_custom_cost", EditRepairForm.cost)
async def enter_custom_cost(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Хорошо, введите итоговую стоимость:")
    await callback.answer()


@router.message(RepairForm.notes)
async def process_notes(message: Message, state: FSMContext):
    await state.update_data(notes=message.text)
    await finalize_repair_creation(message, state)


@router.callback_query(F.data == "skip_notes", RepairForm.notes)
async def skip_notes(callback: CallbackQuery, state: FSMContext):
    await state.update_data(notes="-")
    await finalize_repair_creation(callback.message, state)
    await callback.answer()


async def finalize_repair_creation(message: Message, state: FSMContext):
    user_data = await state.get_data()
    new_repair_id = storage.get_next_repair_id()

    user_data["id"] = new_repair_id
    user_data["date"] = datetime.now().strftime("%d.%m.%Y")

    user_data.setdefault("breakdowns", [])
    user_data.setdefault("cost", 0)
    user_data.setdefault("notes", "-")
    user_data.setdefault("namebike", "-")

    storage.add_repair(user_data)

    await message.answer(
        f"✅ Ремонт успешно добавлен!\n\n" + format_repair_details(user_data),
        reply_markup=detail_repair_inline(new_repair_id),
    )
    await state.clear()


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
            f"Введите новое ФИО клиента (текущее: {current_repair_data.get('FIO')}):"
        )
    elif field_name == "contact":
        await state.set_state(EditRepairForm.contact)
        await callback.message.edit_text(
            f"Введите новый контакт (текущий: {current_repair_data.get('contact')}):"
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
            f"Введите новое название велосипеда (текущее: {current_repair_data.get('namebike', '-') }):"
        )
    elif field_name == "breakdowns":
        # Проверяем тип велосипеда для текущего ремонта
        is_mechanics = current_repair_data.get(
            "isMechanics", True
        )  # По умолчанию механический, если не указано
        if is_mechanics:
            await state.set_state(EditRepairForm.breakdowns)
            current_breakdowns_str = ", ".join(
                current_repair_data.get("breakdowns", [])
            )
            await callback.message.edit_text(
                f"Введите новые поломки (можно несколько через запятую) и их стоимость через пробел "
                f"(например: 'Порвана цепь 500, Прокол колеса 200').\n"
                f"Текущие поломки: {current_breakdowns_str if current_breakdowns_str else '-'}:"
            )
        else:  # Если электровелосипед
            await state.set_state(EditRepairForm.e_bike_breakdowns_edit_select)
            # Фильтруем поломки, чтобы показать только те, которые без цены (стандартные)
            # или те, которые были введены без цены изначально
            current_breakdowns_no_cost = [
                b
                for b in current_repair_data.get("breakdowns", [])
                if not re.search(r"\s+\d+$", b)  # Исключаем те, что имеют цену в конце
            ]
            await state.update_data(
                current_edit_repair_id=repair_id
            )  # Сохраняем ID для последующих шагов
            await callback.message.edit_text(
                "Выберите стандартные поломки для электровелосипеда или введите свои (текущие поломки ниже):\n\n"
                + ", ".join(current_repair_data.get("breakdowns", []))
                + "\n\n",
                reply_markup=e_bike_problems_inline(current_breakdowns_no_cost),
            )

    elif field_name == "cost":
        await state.set_state(EditRepairForm.cost)
        current_cost = current_repair_data.get("cost", 0)
        await callback.message.edit_text(
            f"Введите новую стоимость (текущая: {current_cost} руб.):"
        )
    elif field_name == "notes":
        await state.set_state(EditRepairForm.notes)
        await callback.message.edit_text(
            f"Введите новые примечания (текущие: {current_repair_data.get('notes', '-')}):"
        )
    elif field_name == "date":
        await state.set_state(EditRepairForm.date)
        await callback.message.edit_text(
            f"Введите новую дату в формате ДД.ММ.ГГГГ (текущая: {current_repair_data.get('date', '-')}):"
        )

    await callback.answer()


@router.callback_query(
    F.data.startswith("add_e_bike_problem:"),
    EditRepairForm.e_bike_breakdowns_edit_select,
)
async def edit_e_bike_problem_select(callback: CallbackQuery, state: FSMContext):
    problem_text = callback.data.split(":")[1]
    user_data = await state.get_data()
    repair_id = user_data.get(
        "current_edit_repair_id"
    )  # Получаем ID текущего редактируемого ремонта

    if repair_id is None:
        await callback.message.answer(
            "Ошибка: ID ремонта для редактирования не найден.",
            reply_markup=main_reply_kb(),
        )
        await state.clear()
        await callback.answer()
        return

    current_repair_data = storage.get_active_repair_data_by_id(int(repair_id))
    if not current_repair_data:
        await callback.message.answer("Ремонт не найден.", reply_markup=main_reply_kb())
        await state.clear()
        await callback.answer()
        return

    breakdowns = current_repair_data.get("breakdowns", [])[:]  # Копируем список

    if problem_text in breakdowns:
        breakdowns.remove(problem_text)
    else:
        breakdowns.append(problem_text)

    storage.update_repair_field(repair_id, "breakdowns", breakdowns)

    # Обновляем клавиатуру, показывая текущие выбранные (стандартные) поломки
    # Для отображения галочек, нам нужны только те, которые без цены
    breakdowns_no_cost = [b for b in breakdowns if not re.search(r"\s+\d+$", b)]
    await callback.message.edit_reply_markup(
        reply_markup=e_bike_problems_inline(breakdowns_no_cost)
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
    repair_id = user_data.get("current_edit_repair_id")
    current_repair_data = storage.get_active_repair_data_by_id(int(repair_id))
    current_breakdowns_str = ", ".join(current_repair_data.get("breakdowns", []))

    await callback.message.edit_text(
        "Введите свои поломки (можно несколько через запятую) и их стоимость через пробел "
        "(например: 'Замена цепи 500, Настройка тормозов 300').\n"
        "Чтобы пропустить, отправьте '-'."
        f"\nТекущие поломки: {current_breakdowns_str}"
    )
    await callback.answer()


@router.message(EditRepairForm.e_bike_breakdowns_edit_custom)
async def process_edit_e_bike_custom_breakdowns(message: Message, state: FSMContext):
    text = message.text
    user_data = await state.get_data()
    repair_id = user_data.get("current_edit_repair_id")

    if repair_id is None:
        await message.answer(
            "Ошибка: ID ремонта для редактирования не найден.",
            reply_markup=main_reply_kb(),
        )
        await state.clear()
        return

    current_repair_data = storage.get_active_repair_data_by_id(int(repair_id))
    if not current_repair_data:
        await message.answer("Ремонт не найден.", reply_markup=main_reply_kb())
        await state.clear()
        return

    # Разделяем текущие поломки на стандартные (без цены) и кастомные (с ценой)
    existing_standard_breakdowns = [
        b
        for b in current_repair_data.get("breakdowns", [])
        if not re.search(r"\s+\d+$", b)
    ]

    custom_breakdowns_list, calculated_cost = [], 0

    if text != "-":
        custom_breakdowns_list, calculated_cost = parse_breakdowns_with_cost(text)

    final_breakdowns = existing_standard_breakdowns + custom_breakdowns_list

    storage.update_repair_field(repair_id, "breakdowns", final_breakdowns)

    # Пересчитываем общую стоимость из всех поломок
    total_cost_from_breakdowns = 0
    for bd in final_breakdowns:
        match = re.search(r"\s+(\d+)$", bd)
        if match:
            total_cost_from_breakdowns += int(match.group(1))

    storage.update_repair_field(repair_id, "cost", total_cost_from_breakdowns)

    repair = storage.get_active_repair_data_by_id(int(repair_id))
    await message.answer(
        f"✅ Поломки и стоимость обновлены для ремонта ID: {repair_id}.\n\n"
        + format_repair_details(repair),
        reply_markup=detail_repair_inline(repair_id),
    )
    await state.clear()


@router.callback_query(
    F.data == "finish_breakdowns_selection",
    EditRepairForm.e_bike_breakdowns_edit_select,
)
async def finish_edit_e_bike_selection(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    repair_id = user_data.get("current_edit_repair_id")

    if repair_id is None:
        await callback.message.answer(
            "Ошибка: ID ремонта для редактирования не найден.",
            reply_markup=main_reply_kb(),
        )
        await state.clear()
        await callback.answer()
        return

    repair = storage.get_active_repair_data_by_id(int(repair_id))
    if not repair:
        await callback.message.answer("Ремонт не найден.", reply_markup=main_reply_kb())
        await state.clear()
        await callback.answer()
        return

    # Пересчитываем общую стоимость из всех поломок
    total_cost_from_breakdowns = 0
    for bd in repair.get("breakdowns", []):
        match = re.search(r"\s+(\d+)$", bd)
        if match:
            total_cost_from_breakdowns += int(match.group(1))

    storage.update_repair_field(repair_id, "cost", total_cost_from_breakdowns)

    await callback.message.edit_text(
        f"✅ Поломки и стоимость обновлены для ремонта ID: {repair_id}.\n\n"
        + format_repair_details(repair),
        reply_markup=detail_repair_inline(repair_id),
    )
    await state.clear()
    await callback.answer()


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
