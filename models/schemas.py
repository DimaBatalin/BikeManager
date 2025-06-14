# models/schemas.py

from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime


class Contacts(BaseModel):
    phone: Optional[str] = Field(
        default=None,
        description="Номер телефона клиента, например '+7 912 123-45-67'"
    )
    tg_id: Optional[int] = Field(
        default=None,
        description="Telegram ID клиента (целое число)"
    )

    @validator("phone")
    def check_phone_not_empty(cls, v):
        if v is not None and v.strip() == "":
            return None
        return v

    @validator("tg_id")
    def check_tg_id_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("tg_id должен быть положительным целым числом")
        return v


class Repair(BaseModel):
    id: str = Field(
        ...,
        description="Уникальный идентификатор ремонта (например, UUID)"
    )
    date_created: datetime = Field(
        ...,
        description="Дата и время создания в формате ISO 8601"
    )
    fio: str = Field(
        ...,
        min_length=1,
        description="ФИО клиента (строка не должна быть пустой)"
    )
    contacts: Contacts = Field(
        ...,
        description="Контактные данные клиента"
    )
    bike_type: str = Field(
        ...,
        description="Тип велосипеда: 'str' (обычный) или 'electro' (электровелосипед)"
    )
    problems: List[str] = Field(
        ...,
        description="Список поломок (каждая как строка). Должен содержать хотя бы одну строку."
    )
    notes: Optional[str] = Field(
        default="",
        description="Дополнительные примечания (можно пустая строка)"
    )
    cost: int = Field(
        ...,
        ge=0,
        description="Стоимость ремонта в целых рублях, неотрицательное"
    )
    status: str = Field(
        ...,
        description="Статус ремонта: 'active' или 'closed'"
    )
    date_closed: Optional[datetime] = Field(
        default=None,
        description="Дата и время закрытия (ISO 8601). Только для status='closed'."
    )

    @validator("bike_type")
    def bike_type_must_be_valid(cls, v):
        if v not in ("str", "electro"):
            raise ValueError("bike_type должен быть 'str' или 'electro'")
        return v

    @validator("status")
    def status_must_be_valid(cls, v):
        if v not in ("active", "closed"):
            raise ValueError("status должен быть 'active' или 'closed'")
        return v

    @validator("date_closed", always=True)
    def closed_date_required_if_closed(cls, v, values):
        status = values.get("status")
        if status == "closed" and v is None:
            raise ValueError("date_closed обязателен, если status='closed'")
        return v

    @validator("problems", each_item=True)
    def problem_item_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Каждая поломка должна быть непустой строкой")
        return v.strip()
