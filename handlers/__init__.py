from .start_menu import register_handlers as register_start_menu_handlers
from .create_new_repair import register_handlers as register_create_new_repair_handlers
from .edit_repairs import register_handlers as register_edit_repairs_handlers
from .show_active_repairs import (
    register_handlers as register_show_active_repairs_handlers,
)
from .archive import register_handlers as register_archive_handlers
from .reports import register_handlers as register_reports_handlers

__all__ = [
    "register_start_menu_handlers",
    "register_create_new_repair_handlers",
    "register_edit_repairs_handlers",
    "register_show_active_repairs_handlers",
    "register_archive_handlers",
    "register_reports_handlers",
]
