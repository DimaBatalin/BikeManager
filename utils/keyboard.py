# keyboards.py
from aiogram.types import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from utils.formatter import (
    format_name,
)  # Убедитесь, что `utils/formatter.py` существует и содержит `format_name`
from services import (
    storage,
)  # Убедитесь, что `services/storage.py` существует и содержит необходимые функции
from config import (
    ELECTRIC_BIKE_BREAKDOWNS_PATH,
)  # Убедитесь, что `config.py` существует и содержит этот путь


def main_reply_kb() -> ReplyKeyboardMarkup:
    """
    Главное Reply-меню: Действующие ремонты, Отчёты, Архив
    """
    buttons = [
        [KeyboardButton(text="Действующие ремонты"), KeyboardButton(text="Отчёты")],
        [KeyboardButton(text="Архив")],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def active_repairs_inline(active_list: list) -> InlineKeyboardMarkup:
    """
    Inline-клавиатура: по одному ряду на каждый активный ремонт (текст = ФИО, data = "show_{id}"),
    + внизу кнопка "➕ Создать новый ремонт".
    """
    keyboard = []
    for r in active_list:
        fio = format_name(r.get("FIO", "Без имени"))
        rid = r.get("id")
        # Убедитесь, что rid всегда не None
        if rid is not None:
            keyboard.append(
                [InlineKeyboardButton(text=fio, callback_data=f"show_report:{rid}")]
            )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="➕ Создать новый ремонт", callback_data="new_repair"
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def detail_repair_inline(repair_id: str | int) -> InlineKeyboardMarkup:
    """
    Две кнопки: "✏️ Редактировать" (data="edit:{id}") и "✅ Закрыть" (data="close:{id}")
    """
    # Преобразуем repair_id в строку, если он int, для использования в callback_data
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


def e_bike_problems_inline(selected_problems: list = None) -> InlineKeyboardMarkup:
    """
    Список типичных поломок для электровелосипеда, каждая — callback_data="prob:{название}",
    включает галочки для выбранных проблем.
    Внизу кнопка "Готово" (data="finish_breakdowns_selection").
    """
    if selected_problems is None:
        selected_problems = []

    problems = storage._load(ELECTRIC_BIKE_BREAKDOWNS_PATH)

    keyboard = []
    for p in problems:
        emoji = "✅ " if p in selected_problems else "⬜ "
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{emoji}{p}", callback_data=f"add_e_bike_problem:{p}"
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="➡️ Завершить выбор", callback_data="finish_breakdowns_selection"
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def report_options_inline() -> InlineKeyboardMarkup:
    """
    Выбор типа отчёта: "По неделям" (data="report:weeks") и "По месяцам" (data="report:months").
    """
    keyboard = [
        [InlineKeyboardButton(text="По неделям", callback_data="report:weeks")],
        [InlineKeyboardButton(text="По месяцам", callback_data="report:months")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


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
            InlineKeyboardButton(
                text="Дата", callback_data=f"field:date:{repair_id}"
            ),  # New: Add Date option
        ],
        [InlineKeyboardButton(text="Отмена", callback_data=f"cancel_edit:{repair_id}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def select_bike_type_inline() -> InlineKeyboardMarkup:
    """
    Клавиатура для выбора типа велосипеда (механический/электрический).
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


def edit_bike_type_inline(repair_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для изменения типа велосипеда при редактировании.
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Механика", callback_data=f"set_type:True:{repair_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Электровелосипед", callback_data=f"set_type:False:{repair_id}"
                )
            ],
        ]
    )
    return keyboard


def skip_notes_inline_kb() -> InlineKeyboardMarkup:
    """
    Инлайн-клавиатура для пропуска ввода примечаний.
    """
    buttons = [
        [InlineKeyboardButton(text="Без примечаний", callback_data="skip_notes")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def archive_repair_inline(repair_id: int) -> InlineKeyboardMarkup:
    """
    Инлайн-клавиатура для архивированного ремонта.
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="Восстановить", callback_data=f"restore_repair:{repair_id}"
            ),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def report_options_inline_kb() -> InlineKeyboardMarkup:
    """
    Инлайн-клавиатура для выбора типа отчёта (Неделя/Месяц).
    """
    buttons = [
        [
            InlineKeyboardButton(text="За неделю", callback_data="report_type:week"),
            InlineKeyboardButton(text="За месяц", callback_data="report_type:month"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
