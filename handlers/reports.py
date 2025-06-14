from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import services.storage as storage
from utils.keyboard import main_reply_kb, report_options_inline_kb

router = Router()


def register_handlers(dp):
    dp.include_router(router)


@router.message(F.text == "Отчёты")
async def show_report_options(message: Message, state: FSMContext):
    """
    Показывает пользователю опции для выбора типа отчёта.
    """
    await state.set_state(state=None)
    await message.answer(
        "📊 Выберите, за какой период вы хотите получить отчёт:",
        reply_markup=report_options_inline_kb(),
    )


@router.callback_query(F.data.startswith("report_type:"))
async def generate_report(callback: CallbackQuery):
    """
    Генерирует и отправляет отчёт по выбранному типу периода с HTML-форматированием.
    """
    if not callback.data:
        await callback.answer("Ошибка: данные не получены.", show_alert=True)
        return

    period_type = callback.data.split(":")[1]

    await callback.message.edit_text("⏳ Генерирую отчёт, пожалуйста, подождите...")
    await callback.answer()

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

    reports_data = storage.get_reports_data(period_type, num_periods)

    if not reports_data:
        await callback.message.answer(
            f"🚫 За выбранный период нет данных для отчёта.",
            reply_markup=main_reply_kb(),
        )
        return

    # Заголовок отчёта
    response_messages = [f"✨ <b>{title}</b> ✨\n\n"]

    for report in reports_data:
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

    # Сборка и отправка сообщений, учитывая лимит Telegram
    current_message_batch = ""
    for part in response_messages:
        # Проверка, не превысит ли добавление текущей части лимит в 4096 символов
        if (
            len(current_message_batch) + len(part) > 4000
        ):  # Используем чуть меньший лимит для запаса
            await callback.message.answer(
                current_message_batch, reply_markup=main_reply_kb()
            )
            current_message_batch = part  # Начинаем новую порцию
        else:
            current_message_batch += part

    # Отправляем оставшуюся часть сообщения
    if current_message_batch:
        await callback.message.answer(
            current_message_batch, reply_markup=main_reply_kb()
        )

