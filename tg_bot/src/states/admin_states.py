from aiogram.fsm.state import State, StatesGroup


class SendNotificationState(StatesGroup):
    choose_template = State()
    input_text = State()
    confirm = State()


class AddImageState(StatesGroup):
    waiting_for_url = State()
    waiting_for_caption = State()


class AddMemberState(StatesGroup):
    full_name = State()
    partner_name = State()
    phone = State()
    email = State()


class DeleteMemberState(StatesGroup):
    waiting_for_id = State()


class CreateTemplateState(StatesGroup):
    waiting_for_title = State()
    waiting_for_body = State()


class UpdateConfigState(StatesGroup):
    waiting_for_config = State()
