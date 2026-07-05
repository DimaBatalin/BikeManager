"""
Пример файла конфигурации BikeManager.

Скопируйте этот файл в config.py (он в .gitignore и не попадёт в репозиторий)
и заполните реальными значениями.
"""

from pathlib import Path

# Токен Telegram-бота, полученный у @BotFather
TG_TOKEN = "123456:ABC-YOUR-TELEGRAM-BOT-TOKEN"

# ID пользователей Telegram, которым разрешён доступ к боту.
# Узнать свой ID можно, например, у @userinfobot.
ALLOWED_USER_IDS = {
    111111111,
    222222222,
}

# Пути к файлам-хранилищам данных (JSON).
BASE_DIR = Path(__file__).parent
ACTIVE_PATH = BASE_DIR / "data" / "active_repairs.json"
ARCHIVE_PATH = BASE_DIR / "data" / "archive_repairs.json"

# Источники (каналы) поступления ремонтов: ключ -> отображаемое имя.
REPAIR_SOURCES = {
    "avito": "Avito",
    "instagram": "Instagram",
    "walk_in": "Прямое обращение",
    "referral": "По рекомендации",
    "quick": "Быстрый ремонт",
}

# Список стандартных типовых поломок для электровелосипедов
# (показываются в виде чекбоксов при создании/редактировании ремонта).
ELECTRIC_BIKE_BREAKDOWNS_PATH = [
    "Замена аккумулятора",
    "Ремонт контроллера",
    "Замена мотор-колеса",
    "Ремонт проводки",
    "Прошивка/настройка",
]
