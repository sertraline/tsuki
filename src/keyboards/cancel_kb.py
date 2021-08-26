from aiogram.types import ReplyKeyboardMarkup
from aiogram.types import KeyboardButton


def cancel_kb():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    btn_cancel = KeyboardButton("Cancel")
    markup.add(btn_cancel)
    return markup
