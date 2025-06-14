from .start_menu import register_handlers as register_start_menu_handlers
from .active_repairs import register_handlers as register_active_repairs_handlers
from .archive import register_handlers as register_archive_handlers
from .reports import register_handlers as register_reports_handlers

__all__ = [
    "register_start_menu_handlers",
    "register_active_repairs_handlers",
    "register_archive_handlers",
    "register_reports_handlers",
]