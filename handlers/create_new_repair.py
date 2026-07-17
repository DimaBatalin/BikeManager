import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext

import services.storage as storage
from utils.keyboard import (
    detail_repair_inline,
    e_bike_problems_inline,
    select_bike_type_inline,
    skip_notes_inline_kb,
    confirm_total_cost_kb,
    select_repair_source_inline,
    select_fake_source_inline,
    main_reply_kb,
)
from utils.formatter import (
    format_repair_details,
    format_archived_repair_details,
    parse_breakdowns_with_cost,
    mask_contact,
)
from fsm_states import RepairForm, EditRepairForm, FakeRepairForm

from datetime import datetime

logger = logging.getLogger(__name__)

router = Router()


def register_handlers(dp):
    dp.include_router(router)


FAKE_REPAIR_DEFAULTS = {
    "FIO": "Быстрый ремонт",
    "contact": "-",
    "namebike": "-",
    "breakdowns": [],
    "notes": "Быстрое добавление суммы",
    "isMechanics": True,
}


def _parse_amount(raw: str) -> int | None:
    """
    Валидирует введённую сумму: должна быть целым положительным числом.
    Возвращает int или None, если ввод некорректен.
    """
    if raw is None:
        return None
    raw = raw.strip().replace(" ", "")
    if not raw.lstrip("-").isdigit():
        return None
    value = int(raw)
    if value <= 0:
        return None
    return value


async def _create_fake_archived_repair(
    message: Message, amount: int, source: str, user_id: int
) -> None:
    """
    Создаёт быстрый ремонт на заданную сумму с выбранным источником и
    сохраняет его СРАЗУ в архив. Отвечает пользователю карточкой ремонта.
    """
    today = datetime.now().strftime("%d.%m.%Y")
    repair_data = dict(FAKE_REPAIR_DEFAULTS)
    repair_data["repair_type"] = source
    repair_data["cost"] = amount
    repair_data["calculated_cost"] = amount
    repair_data["date"] = today
    repair_data["archive_date"] = today

    new_id = storage.create_archived_repair(repair_data)

    logger.info(
        "Создан быстрый ремонт ID:%s на сумму %s руб. (источник=%s, сразу в архив). "
        "Инициатор user_id=%s.",
        new_id,
        amount,
        source,
        user_id,
    )

    await message.answer(
        "Быстрый ремонт добавлен в архив!\n\n"
        + format_archived_repair_details(repair_data),
        reply_markup=main_reply_kb(),
    )


async def _ask_fake_repair_source(
    message: Message, amount: int, state: FSMContext
) -> None:
    """Сохраняет сумму в состоянии и просит выбрать источник."""
    await state.update_data(fake_amount=amount)
    await state.set_state(FakeRepairForm.waiting_for_source)
    await message.answer(
        f"Сумма: <b>{amount} руб.</b>\nВыберите источник:",
        reply_markup=select_fake_source_inline(),
    )


@router.message(F.text == "Быстрая сумма")
async def start_fake_repair(message: Message, state: FSMContext):
    """Старт быстрого добавления суммы по кнопке из меню."""
    await state.set_state(FakeRepairForm.waiting_for_amount)
    await message.answer(
        "Введите сумму быстрого ремонта (только положительное число, например: 1500):"
    )


@router.message(Command("fake_repair"))
async def cmd_fake_repair(message: Message, command: CommandObject, state: FSMContext):
    """Быстрое добавление суммы: /fake_repair [сумма]."""
    user_id = message.from_user.id

    if command.args:
        amount = _parse_amount(command.args)
        if amount is None:
            logger.warning(
                "Некорректная сумма в /fake_repair от user_id=%s: %r",
                user_id,
                command.args,
            )
            await message.answer(
                "❌ Некорректная сумма. Введите положительное целое число, например:\n"
                "<code>/fake_repair 1500</code>"
            )
            return
        await _ask_fake_repair_source(message, amount, state)
        return

    # Аргумент не передан — запрашиваем сумму отдельным шагом.
    await state.set_state(FakeRepairForm.waiting_for_amount)
    await message.answer(
        "Введите сумму быстрого ремонта (только положительное число, например: 1500):"
    )


@router.message(FakeRepairForm.waiting_for_amount)
async def process_fake_repair_amount(message: Message, state: FSMContext):
    """Обрабатывает введённую сумму и переходит к выбору источника."""
    user_id = message.from_user.id
    amount = _parse_amount(message.text)
    if amount is None:
        logger.warning(
            "Некорректная сумма при вводе быстрой суммы от user_id=%s: %r",
            user_id,
            message.text,
        )
        await message.answer(
            "❌ Некорректная сумма. Введите положительное целое число (например: 1500):"
        )
        return

    await _ask_fake_repair_source(message, amount, state)


@router.callback_query(F.data == "fake_cancel", FakeRepairForm.waiting_for_source)
async def cancel_fake_repair(callback: CallbackQuery, state: FSMContext):
    """Отмена быстрого добавления суммы на шаге выбора источника."""
    await state.clear()
    await callback.message.edit_text("❌ Быстрое добавление отменено.")
    await callback.message.answer("Выберите раздел:", reply_markup=main_reply_kb())
    await callback.answer()


@router.callback_query(
    F.data.startswith("fake_source:"), FakeRepairForm.waiting_for_source
)
async def process_fake_repair_source(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор источника и сохраняет быстрый ремонт сразу в архив."""
    source = callback.data.split(":")[1]
    user_data = await state.get_data()
    amount = user_data.get("fake_amount")

    if amount is None:
        await state.clear()
        await callback.message.edit_text(
            "Произошла ошибка: сумма не найдена. Попробуйте снова."
        )
        await callback.message.answer(
            "Выберите раздел:", reply_markup=main_reply_kb()
        )
        await callback.answer()
        return

    await state.clear()
    # Убираем клавиатуру выбора источника, чтобы нельзя было нажать повторно.
    await callback.message.edit_reply_markup(reply_markup=None)
    await _create_fake_archived_repair(
        callback.message, amount, source, callback.from_user.id
    )
    await callback.answer()


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
        # Раньше имя жёстко ставилось в "Электровелосипед". Теперь спрашиваем
        # название так же, как у механических, чтобы электровелосипеды могли
        # иметь собственные имена (и различаться в списке ремонтов).
        await state.update_data(breakdowns=[])
        await state.set_state(RepairForm.namebike)
        await callback.message.edit_text(
            "Тип: Электровелосипед.\n"
            "Введите название велосипеда (или отправьте «-», чтобы оставить «Электровелосипед»):"
        )
    else:  # Механический велосипед
        await state.set_state(RepairForm.namebike)
        await callback.message.edit_text("Введите название велосипеда:")

    await callback.answer()


@router.message(RepairForm.namebike)
async def process_namebike(message: Message, state: FSMContext):
    """
    Сохраняет название велосипеда и запрашивает поломки.
    Для механического — ввод поломок текстом; для электровелосипеда —
    выбор стандартных поломок кнопками (как и было).
    """
    user_data = await state.get_data()
    is_mechanics = user_data.get("isMechanics", True)

    name = (message.text or "").strip()
    if not is_mechanics and (name == "-" or not name):
        name = "Электровелосипед"
    await state.update_data(namebike=name)

    if is_mechanics:
        await state.set_state(RepairForm.breakdowns)
        await message.answer(
            "Введите поломки (можно несколько через запятую) и их стоимость через пробел (например: 'Порвана цепь 500, Прокол колеса 200'):"
        )
    else:  # Электровелосипед — переходим к выбору стандартных поломок
        await state.set_state(RepairForm.e_bike_breakdowns_select)
        await message.answer(
            "Выберите стандартные поломки или введите свои:",
            reply_markup=e_bike_problems_inline([]),
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
    amount = _parse_amount(message.text)
    if amount is None:
        logger.warning(
            "Некорректная стоимость при создании ремонта от user_id=%s: %r",
            message.from_user.id,
            message.text,
        )
        await message.answer(
            "Пожалуйста, введите положительное числовое значение стоимости."
        )
        return

    await state.update_data(cost=amount)
    await state.set_state(RepairForm.notes)
    await message.answer(
        "Введите примечания к ремонту или пропустите:",
        reply_markup=skip_notes_inline_kb(),
    )


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

    user_data["date"] = datetime.now().strftime("%d.%m.%Y")

    # Установка значений по-умолчанию для необязательных полей
    user_data.setdefault("breakdowns", [])
    user_data.setdefault("cost", 0)
    user_data.setdefault("notes", "-")
    user_data.setdefault("namebike", "-")
    user_data.setdefault("repair_type", "unknown")  # Добавлено поле типа ремонта

    # Атомарно присваиваем ID и сохраняем — устраняет гонку между
    # получением следующего ID и записью ремонта.
    new_repair_id = storage.create_repair(user_data)

    logger.info(
        "Создан новый ремонт ID:%s. Клиент=%s, контакт=%s, стоимость=%s руб. user_id=%s.",
        new_repair_id,
        user_data.get("FIO", "-"),
        mask_contact(user_data.get("contact", "-")),
        user_data.get("cost", 0),
        message.from_user.id if message.from_user else "unknown",
    )

    await message.answer(
        f"✅ Ремонт успешно добавлен!\n\n" + format_repair_details(user_data),
        reply_markup=detail_repair_inline(new_repair_id),
    )
    await state.clear()
