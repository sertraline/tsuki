import asyncio
import numpy as np
import cv2

from aiogram import types
from PIL import Image, ImageChops, ImageEnhance

import exifread
import traceback
import json
import os


class ErrorLevelAnalysis:
    command = 'ela'

    def __init__(self, essence):
        self.bot = essence.bot
        self.sql = essence.sql
        self.logger = essence.logger
        self.dp = essence.dp
        self.helpers = essence.helpers
        self.content = essence.env.CONTENT_DIR

        self.dp.register_message_handler(self.ela_process, commands=[self.command],
                                         content_types=[types.ContentType.TEXT,
                                                        types.ContentType.DOCUMENT,
                                                        types.ContentType.PHOTO],
                                         commands_ignore_caption=False)
        self.logger.debug('INIT ErrorLevelAnalysis')

    async def ela_process(self, message, state):
        self.logger.debug('Entered ELA process')
        await self.helpers.process_album(message, state, self.ela_album)

    async def ela_album(self, message, state):
        self.logger.debug('Entered ela_album')

        dirname = os.path.join(self.content, str(message.from_user.id))
        if not os.path.isdir(dirname):
            os.mkdir(dirname)

        try:
            self.logger.debug("Processing with ELA")
            await self.ela(message, dirname)
        except:
            self.logger.critical(traceback.format_exc())
            await message.reply("Error processing data.")

    async def ela(self, message, dirname):
        tmp_ext = ".tmp_ela.jpg"
        ela_ext = ".artifact_analysis.jpg"
        data = await self.helpers.get_photo(message, dirname, self.bot)
        if not data:
            return
        image, name = data
        basename, ext = os.path.splitext(name)

        tmp_filename = basename + tmp_ext
        ela_filename = basename + ela_ext

        loop = asyncio.get_event_loop()
        self.logger.debug("Run sync ELA in executor")
        await loop.run_in_executor(None, self.ela_sync, *(name, tmp_filename, ela_filename))

        self.logger.debug("Run sync sweep in executor")
        swept = await loop.run_in_executor(None, sweep, *(name, dirname))

        await types.ChatActions.upload_document()
        doc_group = types.MediaGroup()
        doc_group.attach(types.InputMediaDocument(types.InputFile(ela_filename)))
        doc_group.attach(types.InputMediaDocument(types.InputFile(swept[0])))
        doc_group.attach(types.InputMediaDocument(types.InputFile(swept[1])))
        await self.bot.send_media_group(chat_id=message['chat']['id'],
                                        reply_to_message_id=message['message_id'],
                                        media=doc_group)
        for file in swept:
            os.remove(file)
        os.remove(ela_filename)
        os.remove(tmp_filename)

    def ela_sync(self, name, tmp_filename, ela_filename):
        im = Image.open(name).convert('RGB')
        im.save(tmp_filename, 'JPEG', quality=85)

        tmp_filename_im = Image.open(tmp_filename)
        ela_im = ImageChops.difference(im, tmp_filename_im)

        extrema = ela_im.getextrema()
        max_diff = max([ex[1] for ex in extrema])
        scale = 240.0 / max_diff
        ela_im = ImageEnhance.Brightness(ela_im).enhance(scale)
        ela_im.save(ela_filename)


def sweep(path, dirname):
    temp = os.path.join(dirname, 'temp.jpg')
    x = Image.open(path).convert('RGB')
    x.save(temp, quality=90)

    # sweep1 = 100 inb
    # sweep2 = 210 inb
    inw = 255
    inb_sweeps = [100, 210]
    inb = 210
    ing = 0.7

    files = []
    for sw in inb_sweeps:
        img = cv2.imread(temp)
        in_black = np.array([sw, sw, sw], dtype=np.float32)
        in_white = np.array([inw, inw, inw], dtype=np.float32)
        in_gamma = np.array([ing, ing, ing], dtype=np.float32)
        out_black = np.array([0, 0, 0], dtype=np.float32)
        out_white = np.array([255, 255, 255], dtype=np.float32)

        img = np.clip((img - in_black) / (in_white - in_black), 0, 255)
        img = (img ** (1 / in_gamma)) * (out_white - out_black) + out_black
        img = np.clip(img, 0, 255).astype(np.uint8)
        res = os.path.join(dirname, 'gamma_analysis_%d.jpg' % sw)
        cv2.imwrite(res, img)
        files.append(res)
    return files


class Exif:
    command = 'exif'

    def __init__(self, essence):
        self.bot = essence.bot
        self.sql = essence.sql
        self.logger = essence.logger
        self.dp = essence.dp
        self.helpers = essence.helpers
        self.content = essence.env.CONTENT_DIR

        self.dp.register_message_handler(self.get_exif_process, commands=[self.command],
                                         content_types=[types.ContentType.TEXT,
                                                        types.ContentType.DOCUMENT],
                                         commands_ignore_caption=False)
        print('INIT EXIF', self.dp)

    async def get_exif_process(self, message, state):
        print('enter exif process')
        await self.helpers.process_album(message, state, self.get_exif_album)

    async def get_exif_album(self, message, state):
        self.logger.debug("enter exif album")

        dirname = os.path.join(self.content, str(message.from_user.id))
        if not os.path.isdir(dirname):
            os.mkdir(dirname)

        try:
            await self.get_image_exif(message, dirname)
        except:
            self.logger.critical(traceback.format_exc())
            await message.reply("Error processing data.")

    async def get_image_exif(self, message, dirname):
        data = await self.helpers.get_document(message, dirname, self.bot)
        if not data:
            return
        image, name = data
        try:
            f = open(name, 'rb')
            tags = exifread.process_file(f)
            exif_dict = {}
            for tag in tags.keys():
                if tag not in ('JPEGThumbnail', 'TIFFThumbnail'):
                    if str(tags[tag]).startswith('['):
                        exif_dict[tag] = list(tags[tag].values)
                        for c, item in enumerate(exif_dict[tag]):
                            if type(item) == exifread.classes.Ratio:
                                res = item.numerator / item.denominator
                                if str(res).endswith('.0'):
                                    res = int(res)
                                exif_dict[tag][c] = res
                    else:
                        exif_dict[tag] = str(tags[tag])

            if not exif_dict:
                await message.reply("This photo does not contain EXIF.")
                return
            maps_url = None
            if 'GPS GPSLatitude' in exif_dict:
                maps_url = 'https://www.google.com/maps/place?t=k&q='
                lat = exif_dict['GPS GPSLatitude']
                lon = exif_dict['GPS GPSLongitude']
                longitude = f"""{lon[0]}°{lon[1]}'{lon[2]}"{exif_dict['GPS GPSLongitudeRef']}"""
                latitude = f"""{lat[0]}°{lat[1]}'{lat[2]}"{exif_dict['GPS GPSLatitudeRef']}"""
                from urllib import parse
                maps_url += (parse.quote(latitude) + '+' + parse.quote(longitude))
                maps_url = maps_url

            fmt_dict = json.dumps(exif_dict, indent=4, sort_keys=True)
            if len(fmt_dict) > 4000:
                result = os.path.join(dirname, 'exif.txt')
                with open(result, 'w', encoding='utf-8', errors='ignore') as f:
                    f.write(fmt_dict)
                await message.reply_document(types.InputFile(result), caption=maps_url)
            else:
                if not maps_url:
                    await message.reply('<code>'+fmt_dict+'</code>\n',
                                        parse_mode=types.ParseMode.HTML)
                else:
                    await message.reply('<code>'+fmt_dict+'</code>\n'+maps_url,
                                        parse_mode=types.ParseMode.HTML)
        except:
            print(traceback.format_exc())
            await message.reply("Error processing the file.")
            return
