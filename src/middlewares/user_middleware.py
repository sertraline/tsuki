from aiogram import types
from aiogram.dispatcher.middlewares import BaseMiddleware
import logging


def get_from_user(obj):
    x = [
         obj['from'].id,
         obj['from'].first_name,
         obj['from'].last_name,
         obj['from'].username
        ]
    x = [i if i else '' for i in x]
    return x


class UserMiddleware(BaseMiddleware):
    def __init__(self, user_manager):
        super().__init__()
        self.user_manager = user_manager
        self.logger = logging.getLogger('tsuki')
        self.logger.info('INIT Middleware Logger')

    async def on_pre_process_message(self, message: types.Message, data: dict):
        print(message)
        user_data = get_from_user(message)
        user_id, first_name, last_name, username = user_data

        await self.user_manager.user_entry(*user_data)
        user = await self.user_manager.get_user(user_id)
        data['user'] = user

        self.logger.info("MSG < %s %s [%s %s]> %s" % (first_name, last_name,
                                                      username, user_id, message.text))

    async def on_pre_process_inline_query(self, inline_query: types.InlineQuery, data: dict):
        user_data = get_from_user(inline_query)
        user_id, first_name, last_name, username = user_data

        await self.user_manager.user_entry(*user_data)
        user = await self.user_manager.get_user(user_id)
        data['user'] = user

        self.logger.info("INL < %s %s [%s %s]>" % (first_name, last_name, username, user_id))

    async def on_pre_process_callback_query(self, callback_query: types.CallbackQuery, data: dict):
        user_data = get_from_user(callback_query)
        user_id, first_name, last_name, username = user_data

        await self.user_manager.user_entry(*user_data)
        user = await self.user_manager.get_user(user_id)
        data['user'] = user
        self.logger.info("CAL < %s %s [%s %s]> %s" % (first_name, last_name,
                                                      username, user_id, callback_query.data))
