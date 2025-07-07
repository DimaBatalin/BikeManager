from typing import Dict, Any
from re import search
from config import REPAIR_SOURCES


def parse_breakdowns_with_cost(text: str) -> tuple[list[str], int]:
    breakdowns_list = []
    total_cost = 0
    parts = [part.strip() for part in text.split(",")]
    for part in parts:
        match = search(r"\s+(\d+)$", part)
        if match:
            cost = int(match.group(1))
            breakdowns_list.append(part)
            total_cost += cost
        else:
            breakdowns_list.append(part)
    return breakdowns_list, total_cost


def format_repair_details(repair: Dict[str, Any]) -> str:
    """
    Форматирует детали активного ремонта для отображения пользователю.
    Использует HTML-теги для красивого вывода.
    """
    repair_id = repair.get("id")
    fio = repair.get("FIO", "Не указано")
    contact = repair.get("contact", "Не указан")
    is_mechanics = repair.get("isMechanics", False)
    bike_type = "⚙️Механический" if is_mechanics else "⚡️Электровелосипед"
    namebike = repair.get("namebike", "-")
    breakdowns = repair.get("breakdowns", [])
    breakdowns_str = ", ".join(breakdowns) if breakdowns else "-"
    cost = repair.get("cost", 0)
    notes = repair.get("notes", "-")
    date_created = repair.get("date", "Неизвестно")

    repair_name = repair.get("repair_type", False)
    repair_type = REPAIR_SOURCES[repair_name] if repair_name else "Не указано"

    message_text = (
        f"🛠️ <b>Детали Ремонта ID:</b> <code>{repair_id}</code> 🛠️\n"
        f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
        f"👤 <b>Клиент:</b> {fio}\n"
        f"📞 <b>Контакт:</b> <code>{contact}</code>\n"
        f"📅 <b>Дата создания:</b> <code>{date_created}</code>\n"
        f"🔧 <b>Источник:</b> {repair_type}\n"
        f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
        f"🚲 <b>Тип велосипеда:</b> {bike_type}\n"
        f"🔖 <b>Название:</b> {namebike}\n"
        f"🛠️ <b>Поломки:</b> {breakdowns_str}\n"
        f"💰 <b>Стоимость:</b> <code>{cost} руб.</code>\n"
        f"📝 <b>Примечания:</b> <i>{notes}</i>\n"
    )
    return message_text


def format_archived_repair_details(repair: Dict[str, Any]) -> str:
    """
    Форматирует детали архивированного ремонта для отображения пользователю.
    Включает дату архивирования и использует HTML-теги.
    """
    repair_id = repair.get("id")
    fio = repair.get("FIO", "Не указано")
    contact = repair.get("contact", "Не указан")
    is_mechanics = repair.get("isMechanics", False)
    bike_type = "⚙️Механический" if is_mechanics else "⚡️Электровелосипед"
    namebike = repair.get("namebike", "-")
    breakdowns = repair.get("breakdowns", [])
    breakdowns_str = ", ".join(breakdowns) if breakdowns else "-"
    cost = repair.get("cost", 0)
    notes = repair.get("notes", "-")
    date_created = repair.get("date", "Неизвестно")
    archive_date = repair.get("archive_date", "Неизвестно")

    repair_name = repair.get("repair_type", False)
    repair_type = REPAIR_SOURCES[repair_name] if repair_name else "Не указано"

    message_text = (
        f"📦 <b>Архивный Ремонт ID:</b> <code>{repair_id}</code> 📦\n"
        f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
        f"👤 <b>Клиент:</b> {fio}\n"
        f"📞 <b>Контакт:</b> <code>{contact}</code>\n"
        f"📅 <b>Дата создания:</b> <code>{date_created}</code>\n"
        f"📦 <b>Дата архивирования:</b> <code>{archive_date}</code>\n"
        f"🔧 <b>Источник:</b> {repair_type}\n"
        f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
        f"🚲 <b>Тип велосипеда:</b> {bike_type}\n"
        f"🔖 <b>Название:</b> {namebike}\n"
        f"🛠️ <b>Поломки:</b> {breakdowns_str}\n"
        f"💰 <b>Стоимость:</b> <code>{cost} руб.</code>\n"
        f"📝 <b>Примечания:</b> <i>{notes}</i>\n"
    )
    return message_text


def format_name(full_name: str) -> str:
    """Сокращает ФИО в формат 'Фамилия И.О.'"""
    parts = full_name.split()
    if not parts:
        return full_name

    last_name = parts[0]

    initials = []
    if len(parts) > 1:
        initials.append(parts[1][0] + "." if parts[1] else "")
    if len(parts) > 2:
        initials.append(parts[2][0] + "." if parts[2] else "")

    return f"{last_name} {' '.join(initials)}".strip()
