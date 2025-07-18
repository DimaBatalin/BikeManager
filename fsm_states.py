from aiogram.fsm.state import StatesGroup, State


class RepairForm(StatesGroup):
    fio = State()
    repair_type = State()
    contact = State()
    bike_type = State()
    namebike = State()
    breakdowns = State()
    e_bike_breakdowns_select = State()
    e_bike_breakdowns_custom = State()
    cost = State()
    notes = State()


class ReportState(StatesGroup):
    waiting_for_period = State()


class EditRepairForm(StatesGroup):
    select_field = State()
    fio = State()
    contact = State()
    bike_type = State()
    namebike = State()
    breakdowns = State()
    e_bike_breakdowns_edit_select = State()
    e_bike_breakdowns_edit_custom = State()
    cost = State()
    notes = State()
    repair_type = State()
    date = State()
    is_mechanics = State()


class EditArchiveForm(StatesGroup):
    waiting_for_date = State()
