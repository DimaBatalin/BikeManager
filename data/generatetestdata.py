import random
from datetime import datetime, timedelta
import json
import faker

# Настройки генерации
fake = faker.Faker("ru_RU")
START_DATE = datetime(2023, 6, 17)  # 2 года назад от 2025-06-17
END_DATE = datetime(2025, 6, 17)
TOTAL_DAYS = (END_DATE - START_DATE).days

# Стандартные поломки для электровелосипедов
electro_breakdowns = [
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

# Бренды и модели для механических велосипедов
mechanical_bikes = [
    "Trek Fuel EX",
    "Giant Anthem",
    "Specialized Rockhopper",
    "Cube Aim",
    "Scott Aspect",
    "Cannondale Trail",
    "Merida Big Nine",
    "GT Avalanche",
    "Author Solution",
    "Bergamont Helix",
    "Stevens Super Prestige",
    "Focus Raven",
    "Norco Storm",
    "Kona Fire Mountain",
    "Ghost Kato",
]

# Варианты примечаний
notes_options = [
    "Срочный ремонт",
    "Ожидает запчасти",
    "Гарантия",
    "Требуется диагностика",
    "Клиент заберет завтра",
    "Грязная цепь",
    "Нужна замена детали",
    "Предупреждение: клиент опаздывает",
    "Особые пожелания клиента",
    "Проверить после ремонта",
    "Запчасти заказаны",
    "Только диагностика",
]


def generate_contact():
    """Генерация контактных данных"""
    contact_type = random.random()
    if contact_type < 0.4:  # Телефон
        return f"+7 ({random.randint(900, 999)}) {random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(10, 99)}"
    elif contact_type < 0.7:  # Telegram
        username = fake.user_name()
        return f"@{username}" if random.choice([True, False]) else f"t.me/{username}"
    else:  # Email
        return fake.email()


def generate_breakdowns(is_mechanics):
    """Генерация списка поломок"""
    num_breakdowns = random.randint(1, 4)
    breakdowns = []

    for _ in range(num_breakdowns):
        if is_mechanics:
            # Поломки для механических велосипедов
            breakdown = random.choice(
                [
                    "Прокол колеса",
                    "Замена цепи",
                    "Регулировка тормозов",
                    "Замена каретки",
                    "Правка обода",
                    "Замена спиц",
                    "Смазка трансмиссии",
                    "Замена руля",
                    "Регулировка переключателя",
                    "Замена педалей",
                    "Обслуживание вилки",
                    "Замена седла",
                ]
            )
            # 50% вероятности добавить стоимость
            if random.random() < 0.5:
                cost = random.randint(300, 3000)
                breakdown += f" {cost}"
            breakdowns.append(breakdown)
        else:
            # Поломки для электровелосипедов
            if random.random() < 0.9:  # 90% стандартные поломки
                breakdown = random.choice(electro_breakdowns)
            else:  # 10% ручной ввод
                breakdown = random.choice(
                    [
                        "Ремонт контроллера",
                        "Замена батареи",
                        "Диагностика мотора",
                        "Проблемы с дисплеем",
                        "Замена проводки",
                        "Калибровка сенсоров",
                    ]
                )
                # 50% вероятности добавить стоимость
                if random.random() < 0.5:
                    cost = random.randint(500, 5000)
                    breakdown += f" {cost}"
            breakdowns.append(breakdown)

    return breakdowns


def calculate_breakdown_cost(breakdowns):
    """Расчет стоимости ремонта на основе поломок"""
    total = 0
    for b in breakdowns:
        # Пытаемся извлечь стоимость из строки
        parts = b.split()
        if parts and parts[-1].isdigit():
            total += int(parts[-1])
        else:
            # Случайная стоимость для поломок без указанной цены
            total += random.randint(500, 2500)
    return total


def generate_repair_entry(repair_id, date):
    """Генерация одной записи о ремонте"""
    is_mechanics = random.choice([True, False])

    entry = {
        "id": repair_id,
        "FIO": fake.name(),
        "contact": generate_contact(),
        "isMechanics": is_mechanics,
        "namebike": (
            random.choice(mechanical_bikes) if is_mechanics else "Электровелосипед"
        ),
        "date": date.strftime("%d.%m.%Y"),
        "breakdowns": generate_breakdowns(is_mechanics),
        "notes": "",
    }

    # Рассчитанная стоимость
    calculated_cost = calculate_breakdown_cost(entry["breakdowns"])
    entry["calculated_cost"] = calculated_cost

    # Итоговая стоимость (70% совпадает, 30% отличается)
    if random.random() < 0.7:
        entry["cost"] = calculated_cost
    else:
        # Разница 10-30%
        diff = (
            random.uniform(0.9, 1.3)
            if random.choice([True, False])
            else random.uniform(0.7, 0.9)
        )
        entry["cost"] = int(calculated_cost * diff)

    # Примечания (70% пустые)
    if random.random() < 0.3:
        entry["notes"] = random.choice(notes_options)

    return entry


# Генерация данных
archive_repairs = []
active_repairs = []
repair_id = 1

# Генерация по дням
current_date = START_DATE
for day in range(TOTAL_DAYS + 1):
    # Определяем количество ремонтов на день
    if random.random() < 0.8:  # 80% дней: 0 или 6-10 ремонтов
        num_repairs = 0 if random.random() < 0.5 else random.randint(6, 10)
    else:  # 20% дней: 1-5 ремонтов
        num_repairs = random.randint(1, 5)

    # Генерация ремонтов на день
    for _ in range(num_repairs):
        repair = generate_repair_entry(repair_id, current_date)
        repair_id += 1

        # Определение длительности ремонта
        if random.random() < 0.95:  # 95% - обычные ремонты
            repair_duration = random.randint(0, 21)
        else:  # 5% - зависшие ремонты
            repair_duration = random.randint(60, 180)

        archive_date = current_date + timedelta(days=repair_duration)

        # Разделение на архивные и активные
        if archive_date <= END_DATE:
            repair["archive_date"] = archive_date.strftime("%d.%m.%Y")
            archive_repairs.append(repair)
        else:
            active_repairs.append(repair)

    current_date += timedelta(days=1)

# Сохранение в файлы
with open("archive_repairs.json", "w", encoding="utf-8") as f:
    json.dump(archive_repairs, f, ensure_ascii=False, indent=2)

with open("active_repairs.json", "w", encoding="utf-8") as f:
    json.dump(active_repairs, f, ensure_ascii=False, indent=2)


print("Генерация данных завершена!")
print(f"Всего архивных ремонтов: {len(archive_repairs)}")
print(f"Всего активных ремонтов: {len(active_repairs)}")
