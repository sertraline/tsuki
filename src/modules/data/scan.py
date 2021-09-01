import asyncio
import aio_pika
import hashlib
import traceback
import subprocess
import os
import re

from aiogram import types
from aiogram.utils.exceptions import FileIsTooBig, TelegramAPIError
from datetime import datetime, timedelta
from uuid import uuid4


class FileScan:
    check = [
        'image',
        'video',
        'audio',
        'sound',
        'text'
    ]

    def __init__(self, essence):
        self.bot = essence.bot
        self.scan = essence.file_scan
        self.logger = essence.logger
        self.dp = essence.dp
        self.content = essence.env.CONTENT_DIR

        self.vt_client = essence.vt_client
        self.progress = False
        self.forward_downloads = essence.env.FORWARD_DOWNLOAD

        self.dp.register_message_handler(self.parse, content_types=[types.ContentType.DOCUMENT])
        if self.forward_downloads:
            self.forward_channel = int(essence.env.FORWARD_CHANNEL)
            asyncio.get_event_loop().create_task(self.scan_runner())

    async def run_progress(self, message, chat_id=None, m_id=None):
        self.progress = True
        forward = 0
        back = 10

        text = "Scan in progress\n[%s/%s]" % (
            '/' * forward, ' ' * back
        )
        if message:
            msg = await message.reply(text)
        else:
            msg = await self.bot.send_message(chat_id=chat_id,
                                              reply_to_message_id=m_id,
                                              text=text)
        while self.progress:
            await asyncio.sleep(5)
            forward += 1
            back -= 1
            if back <= 0:
                back = 10
                forward = 0
            await self.bot.edit_message_text(chat_id=msg['chat']['id'],
                                             message_id=msg['message_id'],
                                             text="Scan in progress\n[%s/%s]" % (
                                                 '/' * forward, ' ' * back
                                             ))
        await self.bot.delete_message(chat_id=msg['chat']['id'],
                                      message_id=msg['message_id'])

    async def scan_runner(self):
        connection = None
        while True:
            try:
                connection = await aio_pika.connect_robust(
                    "amqp://guest:guest@127.0.0.1/", loop=asyncio.get_event_loop()
                )
                self.logger.debug('aio_pika: Connection established')
                break
            except:
                self.logger.debug('Connection error. Is rabbitmq-server running?')
                await asyncio.sleep(1)
                continue
        while True:
            async with connection:
                channel = await connection.channel()
                queue = await channel.declare_queue('virustotal_results', auto_delete=True)

                async with queue.iterator() as queue_iter:
                    self.logger.debug('iter')
                    async for message in queue_iter:
                        self.logger.debug('process')
                        async with message.process():
                            data = message.body.decode('utf-8').split('\n')
                            sha256 = data[0]
                            result = int(data[1])
                            message_id = data[-1]
                            chat_id = data[-2]

                            if result > 0:
                                query = '%d engines flagged this file as malicious!' % result
                            else:
                                query = 'Virustotal report: no threats found.'
                            query += f'\nhttps://www.virustotal.com/gui/file/{sha256}/detection'

                            await self.bot.send_message(chat_id=chat_id,
                                                        reply_to_message_id=message_id,
                                                        text=query,
                                                        parse_mode=types.ParseMode.HTML)

            await asyncio.sleep(1)

    async def publish_message(self, message):
        connection = await aio_pika.connect_robust(
            "amqp://guest:guest@127.0.0.1/", loop=asyncio.get_event_loop()
        )
        async with connection:
            routing_key = "download_forward"

            channel = await connection.channel()

            self.logger.debug('Publish message %s' % message)
            await channel.default_exchange.publish(
                aio_pika.Message(body=message.encode()),
                routing_key=routing_key,
            )

    async def process_file(self, path, mime, chat, message_id):
        self.logger.debug('Processing file at path "%s"' % path)
        sha256_hash = hashlib.sha256()
        with open(path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        check = await self.scan.get_scan(sha256_hash.hexdigest())
        if check:
            await self.bot.send_message(chat_id=chat,
                                        reply_to_message_id=message_id,
                                        text=check['scan_result'],
                                        parse_mode=types.ParseMode.HTML)
            return

        loop = asyncio.get_event_loop()
        loop.create_task(self.run_progress(None, chat, message_id))

        try:
            if mime == 'application/pdf':
                result = await self.check_pdf(path)
            else:
                result = await self.check_exe(path, sha256_hash)
        except:
            self.logger.debug(traceback.format_exc())
        else:
            await self.bot.send_message(chat_id=chat,
                                        reply_to_message_id=message_id,
                                        text=result,
                                        parse_mode=types.ParseMode.HTML)
            await self.scan.insert_scan(sha256_hash.hexdigest(), result)
        finally:
            self.progress = False

    async def parse(self, message, state):
        if any([i if i in message.document['mime_type'] else None for i in self.check]):
            return

        file_name = str(uuid4())[:6] + message.document.file_name 
        dirname = os.path.join(self.content, str(message.from_user.id))
        if not os.path.isdir(dirname):
            os.mkdir(dirname)
        temp = os.path.join(dirname, file_name)

        document = message.document['file_id']

        if self.forward_downloads and message.document['mime_type'] != 'application/pdf':
            if message.document['file_size'] > 100000000:
                return
            msg = await self.bot.forward_message(chat_id=-self.forward_channel,
                                                 from_chat_id=message['chat']['id'],
                                                 message_id=message['message_id'])
            payload = (f"{message['chat']['id']}_"
                       f"{message['message_id']}_"
                       f"{message.document['mime_type']}_"
                       f"{msg['message_id']}")
            await self.publish_message(payload)
            return
        if message.document['file_size'] > 19999999:
            return
        attempts = 4
        while attempts:
            try:
                self.logger.debug("Download started for %s" % message)
                await self.bot.download_file_by_id(document, temp)
                break
            except FileIsTooBig:
                return
            except aiogram.utils.exceptions.TelegramAPIError:
                self.logger.debug('TelegramAPIError: retrying download')
                await asyncio.sleep(5)
                attempts -= 1
                if attempts:
                    continue
                else:
                    self.logger.debug('Failed to download %s, return' % message)
                    return

        await self.process_file(temp,
                                message.document['mime_type'],
                                message['chat']['id'],
                                message['message_id'])

    async def check_exe(self, temp, sha256_hash):
        loop = asyncio.get_event_loop()
        task = loop.create_task(self.call_virustotal(temp, sha256_hash))
        result = await task
        return result

    async def check_pdf(self, temp):
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.call_pdfid, temp)
        result = result.decode('utf-8')
        check = re.findall(r'.*?/JavaScript +0.*?', result, flags=re.MULTILINE)
        if check:
            check = re.findall(r'.*?/JS +0.*?', result, flags=re.MULTILINE)
        self.logger.debug("Scan result: <%s, %s>" % (check, result))
        self.progress = False

        if not check and result:
            return f"This file contains javascript!\n<code>{result}</code>"
        else:
            return "This file does <b>not</b> contain any javascript."

    async def call_virustotal(self, path, sha256_hash):
        with open(path, 'rb') as f:
            an = await self.vt_client.scan_file_async(f)
        while True:
            an = await self.vt_client.get_object("/analyses/{}", an.id)
            if an.status == "completed":
                break
            await asyncio.sleep(4)
        an = an.to_dict()
        stats = an['attributes']['stats']
        result = ''
        if stats['malicious']:
            result = "<b>%d</b> engine(s) flagged this file as malicious! (may be a false positive)\n\n" % stats['malicious']
        else:
            result = "Virustotal: nothing suspicious.\n"

        result += f'https://www.virustotal.com/gui/file/{sha256_hash.hexdigest()}/detection'
        return result

    def call_pdfid(self, path):
        try:
            result = subprocess.check_output(['python3', 'src/pdfid/pdfid.py', path], timeout=60)
        except subprocess.TimeoutExpired:
            return
        return result
