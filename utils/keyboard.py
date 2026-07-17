from aiogram.types import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from utils.formatter import (
    format_name,
)
from services import (
    storage,
)
from config import ELECTRIC_BIKE_BREAKDOWNS_PATH, REPAIR_SOURCES

from re import search

def main_reply_kb() -> ReplyKeyboardMarkup:
    buttons = [
        [
            KeyboardButton(text="Действующие ремонты"),
            KeyboardButton(text="➕ Создать новый ремонт"),
        ],
        [
            KeyboardButton(text="Архив"),
            KeyboardButton(text="Отчёты"),
        ],
        [
            KeyboardButton(text="Быстрая сумма"),
        ],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def select_repair_source_inline() -> InlineKeyboardMarkup:
    """
    Клавиатура для выбора источника/типа ремонта.
    """
    buttons = []
    for key, value in REPAIR_SOURCES.items():
        buttons.append(
            [InlineKeyboardButton(text=value, callback_data=f"set_source:{key}")]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def select_fake_source_inline() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора источника для быстрого добавления суммы.
    Отдельный префикс callback ('fake_source:'), чтобы не пересекаться
    с обычным созданием ремонта ('set_source:').
    """
    buttons = []
    for key, value in REPAIR_SOURCES.items():
        buttons.append(
            [InlineKeyboardButton(text=value, callback_data=f"fake_source:{key}")]
        )
    buttons.append(
        [InlineKeyboardButton(text="❌ Отмена", callback_data="fake_cancel")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def source_filter_inline_kb(prefix: str) -> InlineKeyboardMarkup:
    """
    Клавиатура для фильтрации по источнику в архиве и отчетах.
    `prefix` должен быть 'archive_filter' или 'report_filter'.
    """
    buttons = [
        [InlineKeyboardButton(text="Показать все", callback_data=f"{prefix}:all")]
    ]
    for key, value in REPAIR_SOURCES.items():
        buttons.append(
            [InlineKeyboardButton(text=value, callback_data=f"{prefix}:{key}")]
        )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def active_repairs_inline(active_list: list = []) -> InlineKeyboardMarkup:
    keyboard = []
    for r in active_list:
        fio = format_name(r.get("FIO", "Без имени"))
        namebike = (r.get("namebike") or "").strip()
        # К ФИО добавляем название велосипеда, чтобы ремонты было легче
        # различать в списке (например: "Иванов — Trek Fuel EX").
        button_text = f"{fio} — {namebike}" if namebike and namebike != "-" else fio
        rid = r.get("id")
        if rid is not None:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        text=button_text,
                        callback_data=f"show_active_repair_details:{rid}",
                    )
                ]
            )
    if active_list:
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    keyboard.append(
        [
            InlineKeyboardButton(
                text="➕ Создать новый ремонт", callback_data="new_repair"
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def detail_repair_inline(repair_id: str | int) -> InlineKeyboardMarkup:
    str_repair_id = str(repair_id)
    keyboard = [
        [
            InlineKeyboardButton(
                text="✏️ Редактировать", callback_data=f"edit_repair:{str_repair_id}"
            ),
            InlineKeyboardButton(
                text="✅ Закрыть", callback_data=f"close_repair:{str_repair_id}"
            ),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def e_bike_problems_inline(selected_problems: list = []) -> InlineKeyboardMarkup:
    problems = ELECTRIC_BIKE_BREAKDOWNS_PATH
    buttons = []

    base_selected = set()
    for bd in selected_problems:
        base = bd.rsplit(" ", 1)[0] if search(r"\s+\d+$", bd) else bd
        base_selected.add(base)

    for problem in problems:
        is_selected = problem in base_selected
        button_text = f"{'✅' if is_selected else '⬜'} {problem}"
        callback_data = f"add_e_bike_problem:{problem}"
        buttons.append(
            [InlineKeyboardButton(text=button_text, callback_data=callback_data)]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="✍️ Ввести свои поломки", callback_data="input_custom_breakdowns"
            )
        ]
    )
    buttons.append(
        [
            InlineKeyboardButton(
                text="✅ Завершить выбор", callback_data="finish_breakdowns_selection"
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)




def edit_repair_options_inline(repair_id: int) -> InlineKeyboardMarkup:
    """
    Инлайн-клавиатура для выбора поля для редактирования ремонта.
    """
    buttons = [
        [
            InlineKeyboardButton(text="ФИО", callback_data=f"field:FIO:{repair_id}"),
            InlineKeyboardButton(
                text="Контакт", callback_data=f"field:contact:{repair_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="Источник", callback_data=f"field:repair_type:{repair_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="Тип велосипеда", callback_data=f"field:isMechanics:{repair_id}"
            ),
            InlineKeyboardButton(
                text="Название велосипеда", callback_data=f"field:namebike:{repair_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="Поломки", callback_data=f"field:breakdowns:{repair_id}"
            ),
            InlineKeyboardButton(
                text="Стоимость", callback_data=f"field:cost:{repair_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="Примечания", callback_data=f"field:notes:{repair_id}"
            ),
            InlineKeyboardButton(text="Дата", callback_data=f"field:date:{repair_id}"),
        ],
        [InlineKeyboardButton(text="Отмена", callback_data=f"cancel_edit:{repair_id}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def select_bike_type_inline() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Механический велосипед",
                    callback_data="set_bike_type:mechanics",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Электровелосипед", callback_data="set_bike_type:electric"
                )
            ],
        ]
    )
    return keyboard


def edit_bike_type_inline(repair_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для редактирования типа велосипеда.
    ID ремонта (repair_id) здесь не используется в callback_data,
    так как он получается из состояния FSM, но принимается для единообразия.
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Механический велосипед",
                    callback_data="set_bike_type:mechanics",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Электровелосипед", callback_data="set_bike_type:electric"
                )
            ],
        ]
    )
    return keyboard


def skip_notes_inline_kb() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="Без примечаний", callback_data="skip_notes")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def archive_repair_inline(repair_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="♻️ Восстановить", callback_data=f"restore_repair:{repair_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="✏️ Изменить дату", callback_data=f"edit_archive_date:{repair_id}"
            ),
            InlineKeyboardButton(
                text="🗑️ Удалить навсегда", callback_data=f"delete_repair:{repair_id}"
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def report_options_inline_kb() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="По неделям", callback_data="report_type:week"),
            InlineKeyboardButton(text="По месяцям", callback_data="report_type:month"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_total_cost_kb(suggested_cost: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=f"✅ Принять {suggested_cost} руб.",
                callback_data=f"confirm_cost:{suggested_cost}",
            ),
        ],
        [
            InlineKeyboardButton(
                text="✍️ Ввести другую сумму", callback_data="enter_custom_cost"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def archive_pagination_kb(
    page: int, total_pages: int, repair_id: int
) -> InlineKeyboardMarkup:
    buttons = [[]]
    if page > 0:
        buttons[0].append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"archive_page:{page-1}")
        )
    buttons[0].append(
        InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="ignore")
    )
    if page < total_pages - 1:
        buttons[0].append(
            InlineKeyboardButton(
                text="Вперед ➡️", callback_data=f"archive_page:{page+1}"
            )
        )
    buttons.extend(archive_repair_inline(repair_id).inline_keyboard)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def edit_repair_type_keyboard(repair_id):
    # Создаем клавиатуру с вариантами источников
    buttons = []
    for key, name in storage.get_repair_sources().items():
        buttons.append(
            InlineKeyboardButton(
                text=name, callback_data=f"set_repair_source:{key}:{repair_id}"
            )
        )

    # Добавляем кнопку отмены
    buttons.append(
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_edit:{repair_id}")
    )

    # Группируем кнопки по 2 в ряд
    return InlineKeyboardMarkup(
        inline_keyboard=[buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    )
