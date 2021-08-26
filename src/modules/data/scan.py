import asyncio
import hashlib
import traceback
import subprocess
import os
import re

from aiogram import types
from aiogram.utils.exceptions import FileIsTooBig
from uuid import uuid4


class FileScan:
    check = [
        'application/x-ms-dos-executable',
        'application/pdf',
        'application/zip',
        'application/rar'
        'application/x-rar-compressed',
        'application/x-zip-compressed',
    ]

    def __init__(self, essence):
        self.bot = essence.bot
        self.scan = essence.file_scan
        self.logger = essence.logger
        self.dp = essence.dp
        self.content = essence.env.CONTENT_DIR

        self.vt_client = essence.vt_client
        self.progress = False

        self.dp.register_message_handler(self.parse, content_types=[types.ContentType.DOCUMENT])

    async def run_progress(self, message):
        self.progress = True
        forward = 0
        back = 10
        msg = await message.reply("<code>Scan in progress\n[%s/%s]</code>" % (
            '/' * forward, ' ' * back
        ), parse_mode=types.ParseMode.HTML)
        while self.progress:
            forward += 1
            back -= 1
            if back <= 0:
                back = 10
                forward = 0
            await self.bot.edit_message_text(chat_id=msg['chat']['id'],
                                             message_id=msg['message_id'],
                                             text="Scan in progress\n[%s/%s]" % (
                                                 '/' * forward, ' ' * back
                                             ),
                                             parse_mode=types.ParseMode.HTML
                                             )
            await asyncio.sleep(5)
        await asyncio.sleep(1)
        await self.bot.delete_message(chat_id=msg['chat']['id'],
                                      message_id=msg['message_id'])

    async def parse(self, message, state):
        if not any([i if i == message.document['mime_type'] else '' for i in self.check]):
            return

        file_name = str(uuid4())[:6] + message.document.file_name 
        dirname = os.path.join(self.content, str(message.from_user.id))
        if not os.path.isdir(dirname):
            os.mkdir(dirname)
        temp = os.path.join(dirname, file_name)

        document = message.document['file_id']
        if message.document['file_size'] > 19999999:
            return

        try:
            self.logger.debug("Download started for %s" % message)
            await self.bot.download_file_by_id(document, temp)
        except FileIsTooBig:
            return

        sha256_hash = hashlib.sha256()
        with open(temp, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        check = await self.scan.get_scan(sha256_hash.hexdigest())
        if check:
            await message.reply(check['scan_result'], parse_mode=types.ParseMode.HTML)
            return

        loop = asyncio.get_event_loop()
        loop.create_task(self.run_progress(message))

        try:
            if message.document['mime_type'] == 'application/pdf':
                result = await self.check_pdf(temp)
            else:
                result = await self.check_exe(temp, sha256_hash)
        except:
            self.logger.debug(traceback.format_exc())
        else:
            await message.reply(result, parse_mode=types.ParseMode.HTML)
            await self.scan.insert_scan(sha256_hash.hexdigest(), result)
        finally:
            self.progress = False

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
            for key, val in an['attributes']['results'].items():
                if an['attributes']['results'][key]['result']:
                    result += f"<code>{key}: {str(an['attributes']['results'][key]['result'])}</code>\n"
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
