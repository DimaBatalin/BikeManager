"""
Пример файла конфигурации BikeManager.

Скопируйте этот файл в config.py (он в .gitignore и не попадёт в репозиторий)
и заполните реальными значениями.
"""

from pathlib import Path

# Токен Telegram-бота, полученный у @BotFather
TG_TOKEN = "123456:ABC-YOUR-TELEGRAM-BOT-TOKEN"

# Прокси для подключения к Telegram. Нужен, если прямой доступ к Telegram
# закрыт (например, на сервере в РФ). Формат: "socks5://HOST:PORT" или
# "http://HOST:PORT". Если прокси не нужен — оставьте None.
# Пример локального SOCKS5-прокси:
#   PROXY_URL = "socks5://127.0.0.1:10808"
PROXY_URL = None

# ID пользователей Telegram, которым разрешён доступ к боту.
# Узнать свой ID можно, например, у @userinfobot.
ALLOWED_USER_IDS = [
    111111111,
    222222222,
]

# Пути к файлам-хранилищам данных (JSON).
BASE_DIR = Path(__file__).parent
ACTIVE_PATH = BASE_DIR / "data" / "active_repairs.json"
ARCHIVE_PATH = BASE_DIR / "data" / "archive_repairs.json"

# Источники (каналы) поступления ремонтов: ключ -> отображаемое имя.
REPAIR_SOURCES = {
    "familiar": "Знакомые",
    "avito": "Авито",
    "scooter": "Самокат",
    "outsourcing": "Аутсорсинг",
}

# Стандартные типовые поломки для электровелосипедов
# (показываются в виде чекбоксов при создании/редактировании ремонта).
ELECTRIC_BIKE_BREAKDOWNS_PATH = [
    "Прокол колеса",
    "Ремонт рельс",
    "Замена переднего крыла",
    "Замена заднего крыла",
    "Ремонт фары",
    "Ремонт седла",
    "Правка шатунов",
    "Прокачка тормоза",
    "Установка цепи",
]
