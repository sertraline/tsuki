import aiohttp
from aiogram.utils.markdown import hide_link
from aiogram import types
from datetime import datetime

from mimesis.schema import Field
from mimesis.builtins import RussiaSpecProvider, USASpecProvider
from random import choice

from faker import Faker
from aiogram.types import ReplyKeyboardMarkup
from aiogram.types import KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


async def get_male_photo(age):
    base_url = 'https://fakeface.rest/face/json?gender=male&minimum_age=%d&maximum_age=%d'
    async with aiohttp.ClientSession() as sess:
        async with sess.get(base_url % (age - 5, age + 10)) as resp:
            json = await resp.json()
            return json['image_url']


async def get_female_photo(age):
    base_url = 'https://fakeface.rest/face/json?gender=female&minimum_age=%d&maximum_age=%d'
    async with aiohttp.ClientSession() as sess:
        async with sess.get(base_url % (age - 5, age + 10)) as resp:
            json = await resp.json()
            return json['image_url']


class IdentityGenerator:
    command = 'faker'

    def __init__(self, essence):
        self.bot = essence.bot
        self.logger = essence.logger
        self.dp = essence.dp
        self.content = essence.env.CONTENT_DIR

        self.btns = [
            ('🇷🇺', 'ru_RU'),
            ('🇺🇸', 'en_US'),
        ]

        self.dp.register_message_handler(self.faker_entry, commands=[self.command])
        self.dp.register_callback_query_handler(self.identity_process,
                                                lambda c: c.data and c.data.startswith('gen1_'))
        self.dp.register_callback_query_handler(self.back_gen,
                                                lambda c: c.data and c.data.startswith('back_gen'))

    async def faker_entry(self, message, state):
        from_id = message['from']['id']
        menu = InlineKeyboardMarkup()
        for c in range(0, len(self.btns), 2):
            btn_0 = InlineKeyboardButton(self.btns[c][0],
                                         callback_data=f'gen1_'+self.btns[c][1]+f'_{from_id}')
            btn_1 = InlineKeyboardButton(self.btns[c+1][0],
                                         callback_data=f'gen1_'+self.btns[c+1][1]+f'_{from_id}')
            menu.row(btn_0, btn_1)
        await self.bot.send_message(chat_id=message['chat']['id'],
                                    text="Available countries:",
                                    parse_mode=types.ParseMode.HTML,
                                    reply_markup=menu)

    async def back_gen(self, callback):
        cdata = callback.data.split('_')
        from_id = cdata[-1]

        if str(callback['from']['id']) != str(from_id):
            await callback.answer('Go away')
            return

        await callback.answer()
        menu = InlineKeyboardMarkup()
        btns = [
            ('🇷🇺', 'ru_RU'),
            ('🇺🇸', 'en_US'),
        ]
        for c in range(0, len(btns), 2):
            btn_0 = InlineKeyboardButton(btns[c][0], callback_data=f'gen1_'+btns[c][1]+f'_{from_id}')
            btn_1 = InlineKeyboardButton(btns[c+1][0], callback_data=f'gen1_'+btns[c+1][1]+f'_{from_id}')
            menu.row(btn_0, btn_1)
        try:
            await self.bot.edit_message_text(chat_id=callback.message['chat']['id'],
                                             message_id=callback.message['message_id'],
                                             text="Available countries:",
                                             parse_mode=types.ParseMode.HTML,
                                             reply_markup=menu)
        except Exception as e:
            print(e)

    async def identity_process(self, callback):
        cdata = callback.data.split('_')
        locale = f'{cdata[1]}_{cdata[2]}'
        from_id = cdata[-1]

        if str(callback['from']['id']) != str(from_id):
            await callback.answer('Go away')
            return

        await callback.answer()
        retry_kb = InlineKeyboardMarkup()
        btn_0 = InlineKeyboardButton('🔄', callback_data=callback.data)
        back = InlineKeyboardButton('◀️ Back', callback_data='back_gen'+f"_{from_id}")
        retry_kb.row(btn_0)
        retry_kb.row(back)

        funcs = {
            'ru_RU': russian_info,
            'en_US': usa_info
        }

        await self.bot.edit_message_text(chat_id=callback.message['chat']['id'],
                                         message_id=callback.message['message_id'],
                                         text=await funcs[locale](locale),
                                         parse_mode=types.ParseMode.HTML,
                                         reply_markup=retry_kb)


async def russian_info(locale):
    f = Faker(locale)
    p = Field('ru', providers=(RussiaSpecProvider,))
    genders = ['m', 'f']

    while True:
        birth = f.date_of_birth()
        year = birth.year
        current = datetime.now().year
        age = int(current) - int(year)
        if age < 20 or age > 50:
            continue
        break

    g = choice(genders)
    if g == 'm':
        while True:
            weight = p('weight')
            if weight < 50 or weight > 90:
                continue
            break
        name = f.name_male()
        photo_url = await get_male_photo(age)
    else:
        while True:
            weight = p('weight')
            if weight < 40 or weight > 80:
                continue
            break
        name = f.name_female()
        photo_url = await get_female_photo(age)

    addr = f.address().replace('\n', ' ').split()
    addr, postal = ' '.join(addr[:-1]), addr[-1]
    addr = addr.strip(',')

    vehicle = f.license_plate()
    vehicle_cat = f.vehicle_category()

    bank = f.bank()
    bban = f.bban()
    bic = f.bic()
    iban = f.iban()
    swift = f.swift()
    company = f.company()
    b_inn = f.businesses_inn()
    b_ogrn = f.businesses_ogrn()

    passport = p('series_and_number')
    snils = p('snils')

    credit = f.credit_card_number()
    expires = f.credit_card_expire()
    cvv = f.credit_card_security_code()
    job = f.job()

    print(photo_url)
    phone = p('telephone')

    msg = f"""
    👥 Имя: {name}
    🎂 Год рождения: {birth}
    📈 Высота: {p('height')}
    🗿 Вес: {weight}
    👨‍🎓 Образование: {p('university')}

    🏡 Адрес: {addr}
    📬 Почтовый индекс: {postal}

    🏷 СНИЛС: {snils}
    📒 Паспорт: {passport}
    📱 Телефон: {phone}

    🚙 Номерной знак: {vehicle}
    🚙 Категория прав: {vehicle_cat}

    💷 Банк: {bank}
    💷 BBAN: {bban}
    💷 BIC: {bic}
    💷 IBAN: {iban}
    💷 SWIFT: {swift}
    💳 Кредитная карта: {credit} {expires} CVC: {cvv}

    🔩 Работа: {job}
    👷 Компания: {company}
    📕 ИНН компании: {b_inn}
    📕 ОГРН компании: {b_ogrn} <a href='{photo_url}'>‌‌‎</a>
    """
    return msg.replace(' '*4, '').strip()


async def usa_info(locale):
    f = Faker(locale)
    p = Field('en', providers=(USASpecProvider,))
    genders = ['m', 'f']

    while True:
        birth = f.date_of_birth()
        year = birth.year
        current = datetime.now().year
        age = int(current) - int(year)
        if age < 20 or age > 50:
            continue
        break

    g = choice(genders)
    if g == 'm':
        while True:
            weight = p('weight')
            if weight < 50 or weight > 90:
                continue
            break
        name = f.name_male()
        photo_url = await get_male_photo(age)
    else:
        while True:
            weight = p('weight')
            if weight < 40 or weight > 80:
                continue
            break
        name = f.name_female()
        photo_url = await get_female_photo(age)

    addr = f.address().replace('\n', ' ').split()
    addr, postal = ' '.join(addr[:-1]), addr[-1]

    vehicle = f.license_plate()

    credit = f.credit_card_number()
    expires = f.credit_card_expire()
    cvv = f.credit_card_security_code()

    company = f.company()
    job = f.job()
    personal_ssn = f.ssn()

    print(photo_url)
    phone = f.phone_number()

    msg = f"""
    👥 Name: {name}
    🎂 Date of birth: {birth}
    📈 Height: {p('height')}
    🗿 Weight: {weight}
    👨‍🎓 Education: {p('university')}

    🏡 Address: {addr}
    📬 Postal code: {postal}

    🏷 SSN: {personal_ssn}
    📱 Phone: {phone}

    🚙 License plate: {vehicle}

    💳 Credit card: {credit} {expires} CVC: {cvv}

    🔩 Job: {job}
    👷 Company: {company} <a href='{photo_url}'>‌‌‎</a>
    """
    return msg.replace(' '*4, '').strip()
