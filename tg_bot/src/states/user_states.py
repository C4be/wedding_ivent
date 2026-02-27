from aiogram.fsm.state import State, StatesGroup


class RSVPState(StatesGroup):
    full_name = State()
    partner_name = State()
    phone = State()
    email = State()
    attendance_day1 = State()
    attendance_day2 = State()
    drink_pref = State()
    confirm = State()


class SendImageState(StatesGroup):
    waiting_for_image = State()
    waiting_for_caption = State()


class SendWishState(StatesGroup):
    waiting_for_wish = State()


class AskQuestionState(StatesGroup):
    waiting_for_question = State()
