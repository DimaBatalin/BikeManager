import random
from datetime import datetime, timedelta
import faker

fake = faker.Faker("ru_RU")

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

bike_names_mech = [
    "Мангуст",
    "Ветерок",
    "Сокол",
    "Комета",
    "Ураган",
    "Спутник",
    "Турист",
    "Стриж",
    "Звезда",
    "Гепард",
    "Барс",
    "Форсаж",
]
bike_names_electro = "Электровелосипед"


def generate_entry(id_):
    is_mech = random.choice([True, False])
    bike_name = random.choice(bike_names_mech) if is_mech else bike_names_electro
    contact = f"89{random.randint(100000000, 999999999)}"
    date = (datetime.today() - timedelta(days=random.randint(0, 365))).strftime(
        "%d.%m.%Y"
    )
    breakdowns = (
        []
        if is_mech
        else random.sample(
            electro_breakdowns, k=random.randint(0, len(electro_breakdowns))
        )
    )
    notes = fake.sentence() if random.random() < 0.5 else ""
    cost = random.randint(100000000, 999999999)

    return {
        "id": id_,
        "date": date,
        "FIO": fake.name(),
        "contact": contact,
        "isMechanics": is_mech,
        "namebike": bike_name,
        "cost": cost,
        "breakdowns": breakdowns,
        "notes": notes,
    }


data = [generate_entry(i) for i in range(100)]
print(data)
