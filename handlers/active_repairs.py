from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from typing import Union
from datetime import datetime
import re

import services.storage as storage
from fsm_states import MakeRepair, EditRepair
from utils.formatter import format_repair_details, format_name
from utils.keyboard import (
    main_reply_kb,
    active_repairs_inline,
    detail_repair_inline,
    e_bike_problems_inline,
    edit_repair_options_inline,
    select_bike_type_inline,
    edit_bike_type_inline,
    skip_notes_inline_kb,
)

router = Router()


def register_handlers(dp):
    dp.include_router(router)


# region show_repairs
@router.message(F.text == "Действующие ремонты")
@router.message(Command("active_repairs"))
async def show_active_repairs_list(message: Message, state: FSMContext):
    state.clear()
    active_list = storage.get_active_repairs()
    if not active_list:
        await message.answer(
            "Сейчас нет активных ремонтов.", reply_markup=active_repairs_inline([])
        )
        return
    await message.answer(
        "Список активных ремонтов:", reply_markup=active_repairs_inline(active_list)
    )


# region new_repair
@router.callback_query(F.data == "new_repair")
@router.message(Command("new_repair"))
async def cmd_new_repair(
    callback_or_message: Union[CallbackQuery, Message], state: FSMContext
):
    if isinstance(callback_or_message, CallbackQuery):
        message = callback_or_message.message
        if message:
            await callback_or_message.answer()
    else:
        message = callback_or_message

    if message:
        await state.set_state(MakeRepair.WAIT_FIO)
        await message.answer("ФИО клиента:")


@router.message(MakeRepair.WAIT_FIO)
async def process_fio(message: Message, state: FSMContext):
    if message.text:
        await state.update_data(FIO=message.text)
        await state.set_state(MakeRepair.WAIT_CONTACT)
        await message.answer("Номер телефона или тг:")
    else:
        await message.answer("Пожалуйста, введите ФИО клиента.")


@router.message(MakeRepair.WAIT_CONTACT)
async def process_contact(message: Message, state: FSMContext):
    if message.text:
        # Можно добавить валидацию номера телефона
        await state.update_data(contact=message.text)
        await state.set_state(MakeRepair.WAIT_BIKE_TYPE)
        await message.answer("Тип велосипеда:", reply_markup=select_bike_type_inline())
    else:
        await message.answer("Пожалуйста, введите контактный телефон.")


@router.callback_query(F.data.startswith("set_bike_type:"), MakeRepair.WAIT_BIKE_TYPE)
async def process_bike_type(callback: CallbackQuery, state: FSMContext):
    if callback.message and callback.data:
        bike_type = callback.data.split(":")[1]
        is_mechanics = bike_type == "mechanics"
        await state.update_data(isMechanics=is_mechanics)

        if is_mechanics:
            await state.set_state(MakeRepair.WAIT_BIKE_NAME_MECHANICS)
            await callback.message.answer("Введите название велосипеда:")
        else:
            await state.update_data(namebike="Электровелосипед")
            await state.set_state(MakeRepair.WAIT_BREAKDOWNS_ELECTRIC)
            # Передаем пустой список для инициализации выбранных поломок
            await callback.message.answer(
                "Выберите поломки:", reply_markup=e_bike_problems_inline([])
            )
        await callback.answer()
    else:
        await callback.answer(
            "Произошла ошибка при выборе типа велосипеда.", show_alert=True
        )


@router.message(MakeRepair.WAIT_BIKE_NAME_MECHANICS)
async def process_bike_name_mechanics(message: Message, state: FSMContext):
    if message.text:
        await state.update_data(namebike=message.text)
        await state.set_state(MakeRepair.WAIT_BREAKDOWNS_MECHANICS)
        await message.answer(
            "Введите поломки через запятую (например, Прокол колеса, Ремонт фары):"
        )
    else:
        await message.answer("Пожалуйста, введите название велосипеда.")


@router.message(MakeRepair.WAIT_BREAKDOWNS_MECHANICS)
async def process_breakdowns_mechanics(message: Message, state: FSMContext):
    if message.text:
        breakdowns = [b.strip() for b in message.text.split(",")]
        await state.update_data(breakdowns=breakdowns)
        await state.set_state(MakeRepair.WAIT_COST)
        await message.answer("Стоимость ремонта:")
    else:
        await message.answer("Пожалуйста, введите поломки.")


@router.callback_query(
    F.data.startswith("add_e_bike_problem:"), MakeRepair.WAIT_BREAKDOWNS_ELECTRIC
)
async def add_e_bike_problem(callback: CallbackQuery, state: FSMContext):
    if callback.data:  # Ensure callback.data exists
        problem = callback.data.split(":")[1]
        user_data = await state.get_data()
        current_breakdowns = user_data.get("breakdowns", [])
        if problem not in current_breakdowns:
            current_breakdowns.append(problem)
        else:
            current_breakdowns.remove(problem)
        await state.update_data(breakdowns=current_breakdowns)

        # Directly use edit_reply_markup on callback.message if it exists
        if callback.message:
            await callback.message.edit_reply_markup(
                reply_markup=e_bike_problems_inline(current_breakdowns)
            )
        await callback.answer()  # Always answer the callback
    else:
        await callback.answer(
            "Произошла ошибка при добавлении поломки.", show_alert=True
        )


@router.callback_query(
    F.data == "finish_breakdowns_selection", MakeRepair.WAIT_BREAKDOWNS_ELECTRIC
)
async def finish_e_bike_problems(callback: CallbackQuery, state: FSMContext):
    if callback.message:
        user_data = await state.get_data()
        breakdowns = user_data.get("breakdowns", [])
        if not breakdowns:
            await callback.answer(
                "Пожалуйста, выберите хотя бы одну поломку.", show_alert=True
            )
            return

        await state.set_state(MakeRepair.WAIT_COST)
        await callback.message.answer("Стоимость ремонта:")
        await callback.answer()
    else:
        await callback.answer(
            "Произошла ошибка при завершении выбора поломок.", show_alert=True
        )


@router.message(MakeRepair.WAIT_COST)
async def process_cost(message: Message, state: FSMContext):
    if message.text:
        try:
            cost = int(message.text)
            await state.update_data(cost=cost)
            await state.set_state(MakeRepair.WAIT_NOTES)
            await message.answer(
                "Введите примечания к ремонту (необязательно) или нажмите 'Без примечаний':",
                reply_markup=skip_notes_inline_kb(),
            )
        except ValueError:
            await message.answer("Некорректная стоимость. Введите число.")
    else:
        await message.answer("Пожалуйста, введите стоимость.")


@router.callback_query(F.data == "skip_notes", MakeRepair.WAIT_NOTES)
async def skip_notes_callback(callback: CallbackQuery, state: FSMContext):
    if callback.message:
        await state.update_data(notes="")  # Устанавливаем примечания как пустую строку

        repair_data = await state.get_data()
        repair_data["id"] = storage.get_next_repair_id()
        repair_data["date"] = datetime.now().strftime("%d.%m.%Y")

        storage.add_repair(repair_data)
        await state.clear()
        await callback.message.answer(
            f"Ремонт для {repair_data['FIO']} успешно добавлен!\n"
            f"Детали:\n{format_repair_details(repair_data)}",
            reply_markup=main_reply_kb(),
            parse_mode="HTML",
        )
        await callback.answer("Примечания пропущены.")
    else:
        await callback.answer(
            "Произошла ошибка при пропуске примечаний.", show_alert=True
        )


@router.message(MakeRepair.WAIT_NOTES)
async def process_notes(message: Message, state: FSMContext):
    if message.text:
        notes = message.text.strip()
    else:
        notes = ""

    await state.update_data(notes=notes)

    repair_data = await state.get_data()
    repair_data["id"] = storage.get_next_repair_id()
    repair_data["date"] = datetime.now().strftime("%d.%m.%Y")

    storage.add_repair(repair_data)
    await state.clear()
    await message.answer(
        f"Ремонт для {repair_data['FIO']} успешно добавлен!\n"
        f"Детали:\n{format_repair_details(repair_data)}",
        reply_markup=main_reply_kb(),
        parse_mode="HTML",
    )


# region show_repair_data
@router.callback_query(F.data.startswith("show_report:"))
async def show_more_about_repair(callback: CallbackQuery):
    if not callback.data:
        await callback.answer("Ошибка: данные не получены", show_alert=True)
        return

    parts = callback.data.split(":")
    if len(parts) < 2:
        await callback.answer("Ошибка формата данных", show_alert=True)
        return

    try:
        repair_id: int = int(parts[1])
    except ValueError:
        await callback.answer("Некорректный ID ремонта.", show_alert=True)
        return

    repair = storage.get_active_repair_data_by_id(repair_id)

    if repair and callback.message:
        await callback.message.answer(
            format_repair_details(repair),
            reply_markup=detail_repair_inline(repair_id),
            parse_mode="HTML",
        )
    elif callback.message:
        await callback.message.answer("Ремонт не найден.")
    await callback.answer()


# region edit_repair
@router.callback_query(F.data.startswith("edit_repair:"))
async def start_edit(callback: CallbackQuery, state: FSMContext):
    if callback.message and callback.data:
        try:
            repair_id = int(callback.data.split(":")[1])
        except ValueError:
            await callback.answer("Некорректный ID ремонта.", show_alert=True)
            return

        repair = storage.get_active_repair_data_by_id(repair_id)
        if repair:
            await state.update_data(repair_id=repair_id, repair=repair)

            # Ensure this keyboard is updated to include 'date'
            await callback.message.answer(
                "Что вы хотите изменить?",
                reply_markup=edit_repair_options_inline(repair_id),
            )
            await state.set_state(EditRepair.CHOOSING_FIELD)
        else:
            await callback.message.answer("Ремонт не найден.")
        await callback.answer()
    else:
        await callback.answer(
            "Произошла ошибка при начале редактирования.", show_alert=True
        )


@router.callback_query(F.data.startswith("field:"), EditRepair.CHOOSING_FIELD)
async def choose_field(callback: CallbackQuery, state: FSMContext):
    if not (callback.message and callback.data):
        await callback.answer(
            "Произошла ошибка при выборе поля для редактирования.", show_alert=True
        )
        return

    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.answer("Ошибка формата данных для поля.", show_alert=True)
        return

    field = parts[1]
    try:
        repair_id = int(parts[2])
    except ValueError:
        await callback.answer("Некорректный ID ремонта в данных поля.", show_alert=True)
        return

    await state.update_data(edit_field=field, repair_id=repair_id)

    user_data = await state.get_data()
    repair = user_data.get("repair")
    if not repair:  # If repair data isn't in state, fetch it
        repair = storage.get_active_repair_data_by_id(repair_id)
        if not repair:
            await callback.message.answer("Не удалось найти данные о ремонте.")
            await state.clear()
            await callback.answer()
            return
        await state.update_data(repair=repair)

    if field == "isMechanics":
        await callback.message.answer(
            "Выберите тип велосипеда:", reply_markup=edit_bike_type_inline(repair_id)
        )
        await state.set_state(EditRepair.EDITING_BIKE_TYPE)
    elif field == "breakdowns":
        if repair.get("isMechanics"):
            await callback.message.answer("Введите новые поломки через запятую:")
            await state.set_state(
                EditRepair.EDITING_FIELD
            )  # Reusing EDITING_FIELD for text input
        else:  # Электровелосипед
            current_breakdowns = repair.get("breakdowns", [])
            await callback.message.answer(
                "Выберите новые поломки:",
                reply_markup=e_bike_problems_inline(current_breakdowns),
            )
            await state.set_state(EditRepair.EDITING_BREAKDOWNS_ELECTRIC)
    elif field == "notes":
        await callback.message.answer(
            "Введите новые примечания (если нет, напишите '-'):"
        )
        await state.set_state(
            EditRepair.EDITING_FIELD
        )  # Reusing EDITING_FIELD for text input
    elif field == "cost":
        await callback.message.answer("Введите новую стоимость:")
        await state.set_state(
            EditRepair.EDITING_FIELD
        )  # Reusing EDITING_FIELD for text input
    elif field == "date":  # New field for date editing
        await callback.message.answer(
            "Введите новую дату в формате ДД.ММ.ГГГГ (например, 01.01.2024):"
        )
        await state.set_state(
            EditRepair.EDITING_FIELD
        )  # Reusing EDITING_FIELD for text input
    elif field == "FIO":
        await callback.message.answer("Введите новое ФИО клиента:")
        await state.set_state(EditRepair.EDITING_FIELD)
    elif field == "contact":
        await callback.message.answer("Введите новый контактный телефон:")
        await state.set_state(EditRepair.EDITING_FIELD)
    elif field == "namebike" and repair.get(
        "isMechanics"
    ):  # Only allow editing if it's a mechanical bike
        await callback.message.answer("Введите новое название велосипеда:")
        await state.set_state(EditRepair.EDITING_FIELD)
    else:
        # Fallback for other direct text fields (FIO, contact, namebike for mechanical)
        await callback.message.answer("Введите новое значение:")
        await state.set_state(EditRepair.EDITING_FIELD)

    await callback.answer()


@router.callback_query(F.data.startswith("set_type:"), EditRepair.EDITING_BIKE_TYPE)
async def process_edit_bike_type(callback: CallbackQuery, state: FSMContext):
    if not (callback.message and callback.data):
        await callback.answer(
            "Произошла ошибка при изменении типа велосипеда.", show_alert=True
        )
        return

    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.answer("Ошибка формата данных для типа.", show_alert=True)
        return

    is_mechanics_str = parts[1]
    is_mechanics = is_mechanics_str == "True"

    try:
        repair_id = int(parts[2])
    except ValueError:
        await callback.answer(
            "Некорректный ID ремонта при изменении типа.", show_alert=True
        )
        return

    user_data = await state.get_data()
    current_repair = user_data.get("repair") or storage.get_active_repair_data_by_id(
        repair_id
    )

    if not current_repair:
        await callback.message.answer("Ремонт не найден.")
        await state.clear()
        await callback.answer()
        return

    storage.update_repair_field(repair_id, "isMechanics", is_mechanics)
    await state.update_data(repair_id=repair_id)  # Ensure repair_id is in state

    if is_mechanics:
        storage.update_repair_field(repair_id, "namebike", "")
        storage.update_repair_field(repair_id, "breakdowns", [])

        await state.set_state(EditRepair.EDITING_BIKE_NAME_MECHANICS)
        await callback.message.answer(
            "Тип велосипеда изменен на 'Механический'.\nТеперь введите название велосипеда:"
        )
        await callback.answer("Тип велосипеда обновлен!")
    else:
        storage.update_repair_field(repair_id, "namebike", "Электровелосипед")
        storage.update_repair_field(repair_id, "breakdowns", [])

        await state.set_state(EditRepair.EDITING_BREAKDOWNS_ELECTRIC)

        await callback.message.answer(
            "Тип велосипеда изменен на 'Электровелосипед'. Теперь выберите поломки из списка.",
            reply_markup=e_bike_problems_inline([]),
        )
        await callback.answer("Тип велосипеда обновлен! Выбирайте поломки.")


@router.message(EditRepair.EDITING_BIKE_NAME_MECHANICS)
async def process_edit_bike_name_mechanics(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, введите название велосипеда.")
        return

    user_data = await state.get_data()
    repair_id = user_data.get("repair_id")

    if repair_id is None:
        await message.answer(
            "Ошибка: ID ремонта не найден. Попробуйте начать редактирование заново."
        )
        await state.clear()
        return

    storage.update_repair_field(repair_id, "namebike", message.text)

    await state.set_state(EditRepair.EDITING_BREAKDOWNS_MECHANICS)
    await message.answer(
        "Теперь введите поломки через запятую (например, Прокол колеса, Ремонт фары):"
    )


@router.message(EditRepair.EDITING_BREAKDOWNS_MECHANICS)
async def process_edit_breakdowns_mechanics(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, введите поломки.")
        return

    user_data = await state.get_data()
    repair_id = user_data.get("repair_id")

    if repair_id is None:
        await message.answer(
            "Ошибка: ID ремонта не найден. Попробуйте начать редактирование заново."
        )
        await state.clear()
        return

    breakdowns = [b.strip() for b in message.text.split(",")]
    storage.update_repair_field(repair_id, "breakdowns", breakdowns)

    await state.clear()
    await message.answer(
        f"Название велосипеда и поломки обновлены для ремонта ID: {repair_id}!",
        reply_markup=main_reply_kb(),
    )


@router.callback_query(
    F.data.startswith("add_e_bike_problem:"), EditRepair.EDITING_BREAKDOWNS_ELECTRIC
)
async def edit_e_bike_problem(callback: CallbackQuery, state: FSMContext):
    if not (callback.message and callback.data):
        await callback.answer(
            "Произошла ошибка при редактировании поломки.", show_alert=True
        )
        return

    problem = callback.data.split(":")[1]
    user_data = await state.get_data()
    repair_id = user_data.get("repair_id")

    if repair_id is None:
        await callback.answer(
            "Ошибка: ID ремонта не найден в состоянии.", show_alert=True
        )
        await state.clear()
        return

    repair = storage.get_active_repair_data_by_id(int(repair_id))
    if not repair:
        await callback.answer("Ремонт не найден.", show_alert=True)
        await state.clear()
        return

    current_breakdowns = repair.get("breakdowns", [])
    if problem not in current_breakdowns:
        current_breakdowns.append(problem)
    else:
        current_breakdowns.remove(problem)

    storage.update_repair_field(int(repair_id), "breakdowns", current_breakdowns)

    await callback.message.edit_reply_markup(
        reply_markup=e_bike_problems_inline(current_breakdowns)
    )
    await callback.answer()


@router.callback_query(
    F.data == "finish_breakdowns_selection", EditRepair.EDITING_BREAKDOWNS_ELECTRIC
)
async def finish_edit_e_bike_problems(callback: CallbackQuery, state: FSMContext):
    if callback.message:
        user_data = await state.get_data()
        repair_id = user_data.get("repair_id")

        if repair_id is None:
            await callback.answer(
                "Ошибка: ID ремонта не найден в состоянии.", show_alert=True
            )
            await state.clear()
            return

        repair = storage.get_active_repair_data_by_id(int(repair_id))

        if not repair or not repair.get("breakdowns", []):
            await callback.answer(
                "Пожалуйста, выберите хотя бы одну поломку.", show_alert=True
            )
            return

        await state.clear()
        await callback.message.answer(
            "Поломки успешно обновлены!", reply_markup=main_reply_kb()
        )  # Add reply_markup
        await callback.answer()
    else:
        await callback.answer(
            "Произошла ошибка при завершении выбора поломок.", show_alert=True
        )


@router.message(EditRepair.EDITING_FIELD)
async def process_edit_field(message: Message, state: FSMContext):
    user_data = await state.get_data()
    repair_id = user_data.get("repair_id")
    field = user_data.get("edit_field")
    new_value = message.text

    if repair_id is None or field is None:
        await message.answer(
            "Ошибка: Не удалось определить ремонт или поле для редактирования. Попробуйте снова."
        )
        await state.clear()
        return

    if (
        new_value is None
    ):  # Should not happen with message.text, but good for robustness
        await message.answer("Пожалуйста, введите значение.")
        return

    if field == "cost":
        try:
            new_value = int(new_value)
        except ValueError:
            await message.answer("Некорректная стоимость. Введите число.")
            return
    elif (
        field == "breakdowns"
    ):  # This case is for mechanical bikes, or if user types instead of using buttons
        new_value = [b.strip() for b in new_value.split(",")]
    elif field == "notes":
        new_value = new_value.strip() if new_value.strip() != "-" else ""
    elif field == "date":
        # Validate date format DD.MM.YYYY
        if not re.match(r"^\d{2}\.\d{2}\.\d{4}$", new_value):
            await message.answer(
                "Некорректный формат даты. Введите дату в формате ДД.ММ.ГГГГ."
            )
            return
        # Optional: Add further date validation (e.g., valid day/month/year)
        try:
            datetime.strptime(new_value, "%d.%m.%Y")
        except ValueError:
            await message.answer(
                "Введена недействительная дата (например, 30 февраля). Введите корректную дату."
            )
            return

    storage.update_repair_field(repair_id, field, new_value)
    await state.clear()
    await message.answer(
        f"Поле '{field}' успешно обновлено!", reply_markup=main_reply_kb()
    )
    repair = storage.get_active_repair_data_by_id(repair_id)

    if repair and message:
        await message.answer(
            format_repair_details(repair),
            reply_markup=detail_repair_inline(repair_id),
            parse_mode="HTML",
        )
    elif message:
        await message.answer("Ремонт не найден.")


@router.callback_query(F.data.startswith("cancel_edit:"))
async def cancel_edit(callback: CallbackQuery, state: FSMContext):
    if callback.message:
        await state.clear()
        await callback.message.answer(
            "Редактирование отменено.", reply_markup=main_reply_kb()
        )
        await callback.answer()


# endregion edit_repair


# region close_repair (remains unchanged)
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


# endregion close_repair
