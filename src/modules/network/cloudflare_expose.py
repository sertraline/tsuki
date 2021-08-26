import traceback

import aiohttp
import re
import os

from aiogram import types
from bs4 import BeautifulSoup


BASE_URL = 'https://censys.io/ipv4/_search?q='
Q = '443.https.tls.certificate.parsed.names:%s AND 443.https.get.status_code:200'

headers = {
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                   '(KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'),
    'Referer': 'https://censys.io/ipv4',
    'X-Requested-With': 'XMLHttpRequest',
    'Accept-Encoding': 'gzip, deflate, br',
    'TE': 'Trailers'
}


class CensysSearch:
    command = 'expose'

    def __init__(self, essence):
        self.bot = essence.bot
        self.logger = essence.logger
        self.dp = essence.dp
        self.content = essence.env.CONTENT_DIR
        self.helpers = essence.helpers

        self.dp.register_message_handler(self.censys_process, commands=[self.command])
        self.logger.debug("INIT Censys")

    async def censys_process(self, message, state):
        self.logger.debug("Entered Censys process")

        text = await self.helpers.get_text_or_reply(message, self.command)
        if not text:
            return

        p = '(?:http.*://)?(?P<host>[^:/ ]+).?(?P<port>[0-9]*).*'
        match_host = re.search(p, text)

        try:
            self.logger.debug("Matching host %s" % text)
            result = match_host.group('host')
        except:
            self.logger.debug("Invalid domain, return")
            await message.reply("This domain doesn't seem to be a valid address.")
            return

        try:
            uri = BASE_URL + Q % result
            self.logger.debug("[REQUEST] %s" % uri)
            async with aiohttp.ClientSession(headers=headers) as sess:
                async with sess.get(uri) as resp:
                    t = await resp.text()

            soup = BeautifulSoup(t, features='lxml')
            results = soup.find_all('div', {'class': 'SearchResult'})
            if not results:
                self.logger.debug("Censys: nothing found, return")
                await message.reply('Nothing found.')
                return
            msg = ''
            for result in results:
                ip = result.find('span', {'class': 'ip'})
                ip = ip.text.strip()
                ip = '<b>ADDRESS:</b> ' + ip
                meta = result.find('div', {'class': 'results-metadata'})

                title = meta.find('i', {'title': 'homepage title'})
                proto = meta.find('i', {'title': 'public protocols'})
                if title:
                    title = title.parent.text.strip()
                if proto:
                    proto = proto.parent.text.strip()

                meta = meta.text.replace('<', '&lt;').replace('>', '&gt;').split('\n')
                meta = [i.strip() for i in meta if i.strip()]

                for i in range(len(meta)):
                    if proto:
                        if meta[i] == proto:
                            meta[i] = '<b>PROTO:</b> ' + meta[i]
                    if title:
                        if meta[i] == title:
                            meta[i] = '<b>HEADERS:</b> ' + meta[i]

                meta[0] = '<b>HOST:</b> ' + meta[0]
                meta[-2] = '<b>DOMAIN</b>: ' + meta[-2]
                meta[-1] = '<b>SEARCH KEY:</b> ' + meta[-1]
                meta = '\n'.join(meta)
                msg += '%s\n%s\n\n' % (ip, meta)

            if len(msg) > 4096:
                self.logger.debug("Censys reply is too long: replying as document")
                dirname = os.path.join(self.content, str(message.from_user.id))
                if not os.path.isdir(dirname):
                    os.mkdir(dirname)
                temp = os.path.join(dirname, '%s.txt' % self.command)
                with open(temp, 'w', encoding='utf-8', errors='ignore') as f:
                    f.write(msg)
                await message.reply_document(types.InputFile(temp))
            else:
                self.logger.debug("Censys reply")
                await message.reply(msg, parse_mode=types.ParseMode.HTML)
        except:
            self.logger.critical(traceback.format_exc())
            await message.reply("Error processing data.")
