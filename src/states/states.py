from aiogram.dispatcher.filters.state import State, StatesGroup


class Form(StatesGroup):
    auth = State()


class SearchHideState(StatesGroup):
    awaits_photo = State()


class ExifState(StatesGroup):
    get_exif_awaits_photo = State()
    remove_exif_awaits_photo = State()


class ELAState(StatesGroup):
    awaits_photo = State()


class NetworkResolverState(StatesGroup):
    awaits_query = State()


class CensysDomainState(StatesGroup):
    awaits_domain = State()


class MessageEncoderState(StatesGroup):
    base64_encode = State()
    base64_decode = State()
    hex_encode = State()
    hex_decode = State()
    xor_encode = State()
    xor_key_enc = State()
    rot13_encode = State()
    rot13_decode = State()
    rot47_encode = State()
    rot47_decode = State()

