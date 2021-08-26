from aiogram import types
import binascii
import base64
import codecs
import os


class MessageEncoder:
    base64enc = 'base64encode'
    base64dec = 'base64decode'
    hex_enc = 'hexencode'
    hex_dec = 'hexdecode'
    rot13 = 'rot13'

    def __init__(self, essence):
        self.bot = essence.bot
        self.logger = essence.logger
        self.dp = essence.dp
        self.content = essence.env.CONTENT_DIR
        self.helpers = essence.helpers

        self.dp.register_message_handler(self.base64_encode, commands=[self.base64enc])
        self.dp.register_message_handler(self.base64_decode, commands=[self.base64dec])
        self.dp.register_message_handler(self.hex_encode, commands=[self.hex_enc])
        self.dp.register_message_handler(self.hex_decode, commands=[self.hex_dec])
        self.dp.register_message_handler(self.rot13_coder, commands=[self.rot13])

    async def base64_encode(self, message):
        text = await self.helpers.get_text_or_reply(message, self.base64enc)
        if not text:
            return

        try:
            encoded = base64.b64encode(text.encode('utf-8'))
        except:
            await message.reply("Invalid string.")
            return
        encoded = encoded.decode()

        if len(encoded) > 4096:
            dirname = os.path.join(self.content, str(message['from']['id']))
            if not os.path.isdir(dirname):
                os.mkdir(dirname)
            temp = os.path.join(dirname, 'b64_enc.txt')
            with open(temp, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(encoded)
            await message.reply_document(types.InputFile(temp))
        else:
            await message.reply(encoded)

    async def base64_decode(self, message):
        text = await self.helpers.get_text_or_reply(message, self.base64dec)
        if not text:
            return

        try:
            decoded = base64.b64decode(text)
        except:
            await message.reply("Invalid string.")
            return
        decoded = decoded.decode()

        if len(decoded) > 4096:
            dirname = os.path.join(self.content, str(message['from']['id']))
            if not os.path.isdir(dirname):
                os.mkdir(dirname)
            temp = os.path.join(dirname, 'b64_dec.txt')
            with open(temp, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(decoded)
            await message.reply_document(types.InputFile(temp))
        else:
            await message.reply(decoded)

    async def hex_encode(self, message):
        text = await self.helpers.get_text_or_reply(message, self.hex_enc)
        if not text:
            return

        try:
            msg = binascii.hexlify(text.encode('utf-8'))
        except:
            await message.reply("Invalid string.")
            return

        msg = repr(msg)[2:-1]
        if len(msg) > 4096:
            dirname = os.path.join(self.content, str(message['from']['id']))
            if not os.path.isdir(dirname):
                os.mkdir(dirname)
            temp = os.path.join(dirname, 'hex_enc.txt')
            with open(temp, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(msg)
            await message.reply_document(types.InputFile(temp))
        else:
            await message.reply(msg)

    async def hex_decode(self, message):
        text = await self.helpers.get_text_or_reply(message, self.hex_dec)
        if not text:
            return

        try:
            msg = binascii.unhexlify(text)
        except:
            await message.reply("Invalid string.")
            return

        msg = repr(msg)[2:-1]
        if len(msg) > 4096:
            dirname = os.path.join(self.content, str(message['from']['id']))
            if not os.path.isdir(dirname):
                os.mkdir(dirname)
            temp = os.path.join(dirname, 'hex_dec.txt')
            with open(temp, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(msg)
            await message.reply_document(types.InputFile(temp), )
        else:
            await message.reply(msg, )

    async def rot13_coder(self, message):
        text = await self.helpers.get_text_or_reply(message, self.rot13)
        if not text:
            return

        try:
            msg = codecs.encode(text, 'rot-13')
        except:
            await message.reply("Invalid string.")
            return

        if len(msg) > 4096:
            dirname = os.path.join(self.content, str(message['from']['id']))
            if not os.path.isdir(dirname):
                os.mkdir(dirname)
            temp = os.path.join(dirname, 'rot13_enc.txt')
            with open(temp, 'wb', encoding='utf-8', errors='ignore') as f:
                f.write(msg)
            await message.reply_document(types.InputFile(temp))
        else:
            await message.reply(msg)
