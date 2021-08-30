import asyncio
import shutil

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.redis import RedisStorage2

from src.middlewares import user_middleware
from src.postgres import PostgresInterface
from dataclasses import dataclass
from time import time

from src.states import states

import src.helpers as helpers
import src.models as models
import src.modules as modules

from src.logger import DebugLogging
from src.proxy_queue import ProxyQueue, init_queue
from src.keyboards.collector import KeyboardCollector

import os
import vt


@dataclass
class Env:
    API_TOKEN: str
    VIRUSTOTAL_KEY: str
    FORWARD_DOWNLOAD: int
    FORWARD_CHANNEL: int
    REDIS_PORT: int
    REDIS_HOST: str
    REDIS_DB: int
    CONTENT_DIR: str

    def __init__(self):
        with open('.env', 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('#'):
                    continue
                if not line.strip():
                    continue
                key, val = line.strip().split('=')
                val = int(val) if val.isdigit() else val
                setattr(self, key, val)

        if not os.path.isdir(self.CONTENT_DIR):
            os.mkdir(self.CONTENT_DIR)


class Essence:
    logger = DebugLogging(True).logger
    sql = PostgresInterface(logger.debug)

    keyboards = KeyboardCollector()
    proxy_queue = ProxyQueue()
    states = states

    queue_manager = models.QueueManager(sql)
    user_manager = models.UserManager(sql)
    file_scan = models.FileScan(sql)

    helpers = helpers

    def __init__(self, bot, dp, env, vt_client):
        self.bot = bot
        self.dp = dp
        self.env = env
        self.vt_client = vt_client


async def cleanup(content_dir, logger):
    while True:
        logger.debug("Performing cleanup...")
        try:
            now = time()
            for f in os.listdir(content_dir):
                if not f:
                    continue
                if os.stat(
                        path := os.path.join(content_dir, f)
                ).st_mtime < now - 5 * 60:
                    logger.debug("Removing %s" % path)
                    shutil.rmtree(path)
        except Exception as e:
            print(e)
        await asyncio.sleep(5 *
                            60)


def main():
    env = Env()

    bot = Bot(token=env.API_TOKEN)
    storage = RedisStorage2(
        host=env.REDIS_HOST,
        port=env.REDIS_PORT,
        db=env.REDIS_DB
    )
    dp = Dispatcher(bot, storage=storage)
    vt_client = vt.Client(env.VIRUSTOTAL_KEY)

    deps = Essence(bot, dp, env, vt_client)

    instances = [
        modules.IPResolver(deps),
        modules.CensysSearch(deps),
        modules.MessageEncoder(deps),
        modules.FileScan(deps),
        modules.IdentityGenerator(deps),
        modules.ErrorLevelAnalysis(deps),
        modules.Exif(deps)
    ]

    loop = asyncio.get_event_loop()

    loop.create_task(init_queue(deps.proxy_queue))
    loop.create_task(deps.queue_manager.create())
    loop.create_task(deps.user_manager.create())
    loop.create_task(deps.file_scan.create())
    loop.create_task(cleanup(env.CONTENT_DIR, deps.logger))

    dp.setup_middleware(user_middleware.UserMiddleware(deps.user_manager))
    executor.start_polling(dp, skip_updates=True)


if __name__ == '__main__':
    main()
