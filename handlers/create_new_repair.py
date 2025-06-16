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
