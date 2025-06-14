from aiogram.fsm.state import StatesGroup, State

class MakeRepair(StatesGroup):
    WAIT_FIO = State()
    WAIT_CONTACT = State()
    WAIT_BIKE_TYPE = State()
    WAIT_BIKE_NAME_MECHANICS = State()
    WAIT_BREAKDOWNS_MECHANICS = State()
    WAIT_BREAKDOWNS_ELECTRIC = State()
    WAIT_COST = State()
    WAIT_NOTES = State()

class EditRepair(StatesGroup):
    CHOOSING_FIELD = State()
    EDITING_FIELD = State()
    EDITING_BIKE_TYPE = State()
    EDITING_BREAKDOWNS_ELECTRIC = State()
    EDITING_BIKE_NAME_MECHANICS = State()
    EDITING_BREAKDOWNS_MECHANICS = State()
    EDITING_DATE = State()