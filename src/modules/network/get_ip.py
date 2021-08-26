import asyncio
import re
import os
from subprocess import check_output
from socket import gethostbyname
from geolite2 import geolite2
from aiogram import types


def good_netloc(netloc):
    try:
        gethostbyname(netloc)
        return True
    except:
        return False


class IPResolver:
    command = 'ipresolv'

    def __init__(self, essence):
        self.bot = essence.bot
        self.logger = essence.logger
        self.dp = essence.dp
        self.content = essence.env.CONTENT_DIR
        self.helpers = essence.helpers

        self.dp.register_message_handler(self.ip_process, commands=[self.command])
        self.logger.debug("INIT IPResolver")

    async def ip_process(self, message, state):
        self.logger.debug("Entered ip_process <%s, %s>" % (message, state))

        text = await self.helpers.get_text_or_reply(message, self.command)
        if not text:
            return

        self.logger.debug("Resulting query: %s" % text)
        data = {}

        if '://' in text:
            text = text.split('://')[-1]
        if '/' in text:
            text = text.split('/')[0].strip()

        if '127.0.0.1' in text or 'localhost' in text:
            self.logger.debug("Invalid query to IP resolver, return: %s" % text)
            await message.reply("Invalid query.")
            return

        if not good_netloc(text):
            self.logger.debug("good_netloc FALSE")
            await message.reply("This IP or domain seems to be invalid.")
            return

        p = '(?:http.*://)?(?P<host>[^:/ ]+).?(?P<port>[0-9]*).*'
        match_host = re.search(p, text)
        try:
            self.logger.debug("Matching host")
            result = match_host.group('host')
        except:
            self.logger.debug("Not a domain, query geolite")
            # not a domain
            try:
                data['Geolocation'] = '<b>Geolocation:</b>\n' + self.geolite(text)
            except:
                data['Geolocation'] = '<b>Geolocation:</b>\nNothing found'
        else:
            self.logger.debug("Is a domain, query geolite+whois")
            try:
                ipaddr = gethostbyname(result)
                data['Geolocation'] = '<b>Geolocation:</b>\n' + self.geolite(ipaddr)
                data['Domain IP address'] = '<b>IP address:</b> ' + ipaddr
            except:
                data['Domain IP address'] = '<b>IP address:</b> ' + 'Error resolving data'
            try:
                self.logger.debug("Run whois in executor")

                loop = asyncio.get_event_loop()
                domain = await loop.run_in_executor(
                    None,
                    check_output,
                    ['whois', '%s' % result]
                )

                domain = domain.decode("utf-8")

                self.logger.debug("whois success")

                domain = re.sub(' +', ' ', domain).strip()
                subs = re.findall('^(.{0,20}:.*?)$', domain, flags=re.MULTILINE)
                _filter = ['TERMS OF USE:', 'NOTICE:', 'to:', 'remarks:']
                ex = False
                if len(' '.join(subs)) > 2600:
                    ex = True
                if subs:
                    from html import escape
                    data['whois'] = '<b>WHOIS:</b>\n'
                    for sub in subs:
                        if any([sub.strip().startswith(item) for item in _filter]):
                            continue
                        if ex:
                            if 'Domain Status:' in sub:
                                continue
                        data['whois'] += (escape(sub.strip()) + '\n')
                else:
                    raise Exception
            except Exception as e:
                print(e)
                data['whois'] = '<b>WHOIS:</b>\nNothing found'

        msg = ''
        for key, val in data.items():
            msg += (data[key] + '\n\n')

        if len(msg) > 4096:
            self.logger.debug("IP reply is too long, replying as document")

            dirname = os.path.join(self.content, str(message['from']['id']))
            if not os.path.isdir(dirname):
                os.mkdir(dirname)
            temp = os.path.join(dirname, '%s.txt' % self.command)
            with open(temp, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(msg)

            await message.reply_document(types.InputFile(temp))
        else:
            self.logger.debug("IP reply", msg)
            await message.reply(msg.strip(), parse_mode=types.ParseMode.HTML)

    def geolite(self, ip_addr):
        reader = geolite2.reader()

        result = reader.get(ip_addr)

        if result.get("subdivisions"):
            result = (
                f"<b>GEO ID</b>: {result['country']['geoname_id']}\n"
                f"<b>COUNTRY</b>: {result['country']['names']['en']}\n"
                f"<b>LATITUDE</b>: {result['location']['latitude']}\n"
                f"<b>LONGITUDE</b>: {result['location']['longitude']}\n"
                f"<b>TIMEZONE</b>: {result['location']['time_zone']}\n"
                f"<b>ISO</b>: {result['subdivisions'][0]['iso_code']}\n"
                f"<b>SUBDIVISION GEO ID</b>: {result['subdivisions'][0]['geoname_id']}\n"
                f"<b>SUBDIVISION</b>: {result['subdivisions'][0]['names']['en']}")
        else:
            result = (
                f"<b>GEO ID</b>: {result['country']['geoname_id']}\n"
                f"<b>COUNTRY</b>: {result['country']['names']['en']}\n"
                f"<b>LATITUDE</b>: {result['location']['latitude']}\n"
                f"<b>LONGITUDE</b>: {result['location']['longitude']}")
        return result