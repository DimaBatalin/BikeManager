import json
import logging
import threading
from pathlib import Path
from datetime import datetime, timedelta, date
import config
import calendar
import locale
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Пытаемся установить русскую локаль для названий месяцев в отчётах.
# Если ни один из вариантов не доступен на текущей ОС — просто логируем
# предупреждение и продолжаем работу с локалью по умолчанию (месяцы
# в этом случае будут отображаться на английском, но бот не упадёт).
_LOCALE_CANDIDATES = ("ru_RU.UTF-8", "Russian_Russia.1251", "ru_RU", "ru_RU.CP1251")
for _locale_name in _LOCALE_CANDIDATES:
    try:
        locale.setlocale(locale.LC_ALL, _locale_name)
        break
    except locale.Error:
        continue
else:
    logger.warning(
        "Не удалось установить русскую локаль (пробовали: %s). "
        "Названия месяцев в отчётах будут отображаться на английском.",
        ", ".join(_LOCALE_CANDIDATES),
    )

# RLock (а не Lock), т.к. некоторые функции внутри lock вызывают
# внутренние хелперы, которые тоже могут захватывать блокировку
# (например атомарное создание ремонта с новым ID).
lock = threading.RLock()


def _load(path: Path) -> list:
    """
    Загружает данные из JSON файла по указанному пути.
    Возвращает пустой список, если файл не существует, повреждён
    или недоступен для чтения — чтобы бот не падал целиком из-за
    проблем с одним файлом хранилища.
    """
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        logger.exception("Файл %s повреждён (невалидный JSON).", path)
        return []
    except OSError:
        logger.exception("Не удалось прочитать файл %s.", path)
        return []

    if not isinstance(data, list):
        logger.error(
            "Файл %s содержит неожиданный формат данных (ожидался список).", path
        )
        return []
    return data


def _save(path: Path, data) -> bool:
    """
    Сохраняет данные в JSON файл по указанному пути.
    Пишет во временный файл и атомарно переименовывает его в целевой,
    чтобы при сбое посреди записи не повредить существующие данные.
    Возвращает True при успехе, False при ошибке записи.
    """
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp_path.replace(path)
        return True
    except OSError:
        logger.exception("Не удалось сохранить файл %s.", path)
        return False


def get_active_repairs() -> list:
    """
    Возвращает список всех активных ремонтов.
    """
    return _load(config.ACTIVE_PATH)


def update_active_repairs(all_repairs: list):
    """
    Полностью перезаписывает файл активных ремонтов.
    """
    with lock:
        _save(config.ACTIVE_PATH, all_repairs)


def get_archive_repairs() -> list:
    """
    Возвращает список всех архивных ремонтов.
    """
    return _load(config.ARCHIVE_PATH)


def update_archive_repairs(all_repairs: list):
    """
    Полностью перезаписывает файл архивных ремонтов.
    """
    with lock:
        _save(config.ARCHIVE_PATH, all_repairs)


def _get_next_repair_id_unlocked() -> int:
    """
    Внутренний хелпер: вычисляет следующий ID БЕЗ захвата блокировки.
    Вызывающий код обязан сам держать `lock`.
    """
    active_repairs = _load(config.ACTIVE_PATH)
    archive_repairs = _load(config.ARCHIVE_PATH)
    all_ids = [
        r.get("id", 0)
        for r in active_repairs + archive_repairs
        if isinstance(r.get("id"), int)
    ]
    return max(all_ids) + 1 if all_ids else 1


def get_next_repair_id() -> int:
    """
    Генерирует следующий доступный ID для нового ремонта.
    Ищет максимальный ID среди активных и архивных ремонтов.

    ВНИМАНИЕ: если между вызовом этой функции и последующим add_repair()
    может произойти конкурентная запись — используйте create_repair(),
    которая делает обе операции атомарно под одной блокировкой.
    """
    with lock:
        return _get_next_repair_id_unlocked()


def add_repair(repair_dict: dict) -> bool:
    """
    Добавляет новый ремонт (с уже проставленным ID) в список активных.
    Возвращает True при успешном сохранении.
    """
    with lock:
        data = _load(config.ACTIVE_PATH)
        data.append(repair_dict)
        return _save(config.ACTIVE_PATH, data)


def create_repair(repair_dict: dict) -> int:
    """
    Атомарно генерирует новый ID и добавляет ремонт в активные,
    под одной блокировкой — устраняет гонку между
    get_next_repair_id() и add_repair(), при которой два
    параллельных запроса могли бы получить одинаковый ID.
    Возвращает присвоенный ID.
    """
    with lock:
        new_id = _get_next_repair_id_unlocked()
        repair_dict["id"] = new_id
        data = _load(config.ACTIVE_PATH)
        data.append(repair_dict)
        _save(config.ACTIVE_PATH, data)
        return new_id


def archive_repair_by_id(rid: int) -> bool:
    """
    Перемещает ремонт из активных в архив по ID.
    Возвращает True, если ремонт найден и перемещен, False в противном случае.
    """
    with lock:
        active = _load(config.ACTIVE_PATH)
        archive = _load(config.ARCHIVE_PATH)

        to_move = None
        active_filtered = []
        for r in active:
            if r.get("id") == rid:
                to_move = r
            else:
                active_filtered.append(r)

        if not to_move:
            return False

        to_move["archive_date"] = datetime.now().strftime("%d.%m.%Y")
        archive.append(to_move)

        _save(config.ACTIVE_PATH, active_filtered)
        _save(config.ARCHIVE_PATH, archive)
        return True


def get_active_repair_data_by_id(repair_id: int) -> Optional[dict]:
    """
    Возвращает данные активного ремонта по его ID.
    Возвращает None, если ремонт не найден.
    """
    active_repairs = get_active_repairs()
    for repair in active_repairs:
        if repair.get("id") == repair_id:
            return repair
    return None


def update_repair_field(repair_id: int, field_name: str, new_value) -> bool:
    """
    Обновляет указанное поле у ремонта с заданным ID.
    Работает только для активных ремонтов.
    """
    with lock:
        active_repairs = _load(config.ACTIVE_PATH)
        updated = False
        for repair in active_repairs:
            if repair.get("id") == repair_id:
                repair[field_name] = new_value
                updated = True
                break
        if updated:
            return _save(config.ACTIVE_PATH, active_repairs)
        return False


def get_archived_repairs_last_two_months(source_filter: str = "all") -> list:
    """
    Возвращает список архивированных ремонтов за последние 2 месяца.
    Добавлена фильтрация по источнику (repair_type).
    """
    all_archive_repairs = _load(config.ARCHIVE_PATH)
    two_months_ago = datetime.now() - timedelta(days=60)
    recent_repairs = []
    for repair in all_archive_repairs:
        archive_date_str = repair.get("archive_date")
        if archive_date_str:
            try:
                archive_date = datetime.strptime(archive_date_str, "%d.%m.%Y")
            except ValueError:
                logger.warning(
                    "Некорректная дата архивации %r у ремонта ID:%s — запись пропущена.",
                    archive_date_str,
                    repair.get("id"),
                )
                continue
            if archive_date >= two_months_ago:
                # Применяем фильтр, если он не 'all'
                if (
                    source_filter == "all"
                    or repair.get("repair_type") == source_filter
                ):
                    recent_repairs.append(repair)
    return recent_repairs


def restore_repair_by_id(repair_id: int) -> bool:
    """
    Перемещает ремонт из архива в активные по ID.
    Удаляет поле 'archive_date'.
    Возвращает True, если ремонт найден и перемещен, False в противном случае.
    """
    with lock:
        active = _load(config.ACTIVE_PATH)
        archive = _load(config.ARCHIVE_PATH)

        to_move = None
        archive_filtered = []
        for r in archive:
            if r.get("id") == repair_id:
                to_move = r
            else:
                archive_filtered.append(r)

        if not to_move:
            return False  # Ремонт не найден в архиве

        # Удаляем поле 'archive_date'
        if "archive_date" in to_move:
            del to_move["archive_date"]

        active.append(to_move)

        _save(config.ACTIVE_PATH, active)
        _save(config.ARCHIVE_PATH, archive_filtered)
        return True


def get_repair_sources():
    """Возвращает словарь источников ремонтов"""
    return config.REPAIR_SOURCES


def get_reports_data(
    period_type: str, num_periods: int, source_filter: str = "all"
) -> List[Dict[str, Any]]:
    """
    Собирает данные для отчетов с учетом фильтрации по источнику.
    """
    all_archive_repairs = _load(config.ARCHIVE_PATH)

    # --- НОВЫЙ БЛОК ФИЛЬТРАЦИИ ---
    if source_filter != "all":
        filtered_list = []
        for r in all_archive_repairs:
            if r.get("repair_type") == source_filter:
                filtered_list.append(r)
        all_archive_repairs = filtered_list
    # --- КОНЕЦ БЛОКА ---

    reports = []
    today = datetime.now().date()

    if period_type == "week":
        for i in range(num_periods):
            # Find the Sunday of the current week
            current_sunday = today + timedelta(days=6 - today.weekday())

            # For each iteration, subtract 'i' weeks from this current_sunday
            week_end = current_sunday - timedelta(weeks=i)
            week_start = week_end - timedelta(days=6)

            period_repairs = []
            total_cost = 0
            bike_count = 0

            for repair in all_archive_repairs:
                archive_date_str = repair.get("archive_date")
                if archive_date_str:
                    try:
                        arch_date = datetime.strptime(
                            archive_date_str, "%d.%m.%Y"
                        ).date()
                    except ValueError:
                        logger.warning(
                            "Некорректная дата архивации %r у ремонта ID:%s "
                            "при формировании недельного отчёта — запись пропущена.",
                            archive_date_str,
                            repair.get("id"),
                        )
                        continue
                    if week_start <= arch_date <= week_end:
                        period_repairs.append(repair)
                        total_cost += repair.get("cost", 0)
                        bike_count += 1

            reports.append(
                {
                    "period_name": f"с {week_start.day:02d}.{week_start.month:02d} по {week_end.day:02d}.{week_end.month:02d}",
                    "start_date": week_start.strftime("%d.%m.%Y"),
                    "end_date": week_end.strftime("%d.%m.%Y"),
                    "bike_count": bike_count,
                    "total_cost": total_cost,
                    "repairs": period_repairs,
                }
            )

        reports.reverse()

    elif period_type == "month":
        for i in range(num_periods):
            # Calculate the target month and year
            target_month = today.month - i
            target_year = today.year

            while target_month <= 0:  # Adjust year if month goes below 1
                target_month += 12
                target_year -= 1

            # Get the first day of the target month
            month_start = date(target_year, target_month, 1)
            # Get the last day of the target month
            month_end = date(
                target_year,
                target_month,
                calendar.monthrange(target_year, target_month)[1],
            )

            period_repairs = []
            total_cost = 0
            bike_count = 0

            for repair in all_archive_repairs:
                archive_date_str = repair.get("archive_date")
                if archive_date_str:
                    try:
                        arch_date = datetime.strptime(
                            archive_date_str, "%d.%m.%Y"
                        ).date()
                    except ValueError:
                        logger.warning(
                            "Некорректная дата архивации %r у ремонта ID:%s "
                            "при формировании месячного отчёта — запись пропущена.",
                            archive_date_str,
                            repair.get("id"),
                        )
                        continue
                    if month_start <= arch_date <= month_end:
                        period_repairs.append(repair)
                        total_cost += repair.get("cost", 0)
                        bike_count += 1

            reports.append(
                {
                    "period_name": f"{calendar.month_name[target_month].capitalize()} {target_year}",
                    "start_date": month_start.strftime("%d.%m.%Y"),
                    "end_date": month_end.strftime("%d.%m.%Y"),
                    "bike_count": bike_count,
                    "total_cost": total_cost,
                    "repairs": period_repairs,
                }
            )

        reports.reverse()

    return reports


def update_archive_repair_field(repair_id: int, field_name: str, new_value) -> bool:
    """
    Обновляет указанное поле у ремонта в АРХИВЕ.
    """
    with lock:
        archive_repairs = _load(config.ARCHIVE_PATH)
        updated = False
        for repair in archive_repairs:
            if repair.get("id") == repair_id:
                repair[field_name] = new_value
                updated = True
                break
        if updated:
            return _save(config.ARCHIVE_PATH, archive_repairs)
        return False


def delete_repair_from_archive_by_id(repair_id: int) -> bool:
    """
    Безвозвратно удаляет ремонт из архива по ID.
    Возвращает True, если ремонт найден и удален.
    """
    with lock:
        archive = _load(config.ARCHIVE_PATH)
        original_length = len(archive)

        archive_filtered = [r for r in archive if r.get("id") != repair_id]

        if len(archive_filtered) < original_length:
            return _save(config.ARCHIVE_PATH, archive_filtered)
        return False
