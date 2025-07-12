from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
import services.storage as storage
from utils.keyboard import (
    main_reply_kb,
    report_options_inline_kb,
)
from fsm_states import ReportState

router = Router()


def register_handlers(dp):
    dp.include_router(router)



@router.callback_query(F.data.startswith("report_filter:"))
async def handle_report_source_filter(callback: CallbackQuery, state: FSMContext):
    source_filter = callback.data.split(":")[1]
    await state.set_state(ReportState.waiting_for_period)
    await state.update_data(source_filter=source_filter)
    await callback.message.edit_text(
        "🗓️ Теперь выберите период для отчёта:",
        reply_markup=report_options_inline_kb(),
    )
    await callback.answer()


@router.callback_query(
    F.data.startswith("report_type:"), ReportState.waiting_for_period
)
async def generate_report(callback: CallbackQuery, state: FSMContext):
    if not callback.data:
        await callback.answer("Ошибка: данные не получены.", show_alert=True)
        return

    # Получаем фильтр из состояния
    fsm_data = await state.get_data()
    source_filter = fsm_data.get("source_filter", "all")
    await state.clear()  # Очищаем состояние

    period_type = callback.data.split(":")[1]
    await callback.message.edit_text("⏳ Генерирую отчёт, пожалуйста, подождите...")

    if period_type == "week":
        num_periods = 4
        title = "Отчёты за последние 4 календарные недели"
    elif period_type == "month":
        num_periods = 12
        title = "Отчёты за последние 12 календарных месяцев"
    else:
        await callback.message.answer(
            "❌ Неизвестный тип отчёта.", reply_markup=main_reply_kb()
        )
        return

    # Передаем фильтр в функцию
    reports_data = storage.get_reports_data(period_type, num_periods, source_filter)

    if not reports_data or all(report["bike_count"] == 0 for report in reports_data):
        await callback.message.edit_text(
            f"🚫 В выбранной категории нет данных для отчёта за указанный период.",
        )
        return

    # Формирование заголовка с учетом фильтра
    from utils.keyboard import REPAIR_SOURCES  # Локальный импорт для получения названия

    filter_name = REPAIR_SOURCES.get(source_filter, "Все категории")
    full_title = f"✨ <b>{title}</b>\n(Категория: <b>{filter_name}</b>) ✨\n\n"
    response_messages = [full_title]

    for report in reports_data:
        if report["bike_count"] == 0:
            continue  # Пропускаем пустые периоды

        if period_type == "week":
            period_display = f"с {report['start_date']} по {report['end_date']}"
        else:
            period_display = report["period_name"]

        message_part = (
            f"--- <b>{period_display}</b> ---\n"
            f"  🛠️ <b>Количество ремонтов:</b> <code>{report['bike_count']}</code>\n"
            f"  💰 <b>Общая сумма:</b> <code>{report['total_cost']} руб.</code>\n\n"
        )
        response_messages.append(message_part)

    current_message_batch = ""
    for part in response_messages:
        if len(current_message_batch) + len(part) > 4000:
            await callback.message.answer(
                current_message_batch, reply_markup=main_reply_kb()
            )
            current_message_batch = part
        else:
            current_message_batch += part

    if current_message_batch:
        if callback.message.text.startswith("⏳"):
            await callback.message.edit_text(current_message_batch)
        else:
            await callback.message.answer(
                current_message_batch, reply_markup=main_reply_kb()
            )
