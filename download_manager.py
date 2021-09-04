from telethon.sync import TelegramClient, events
from telethon.tl.types import InputPeerChat
from dataclasses import dataclass
from uuid import uuid4

from src.logger import DebugLogging

import datetime
import aio_pika
import asyncio
import os

if os.name != 'nt':
    import uvloop


@dataclass
class Env:
    TELETHON_API_KEY: int
    TELETHON_API_HASH: str
    CONTENT_DIR: str
    FORWARD_CHANNEL: int

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


async def push(result):
    connection = await aio_pika.connect_robust(
        "amqp://guest:guest@127.0.0.1/", loop=asyncio.get_event_loop()
    )
    async with connection:
        routing_key = "virustotal"

        channel = await connection.channel()

        await channel.default_exchange.publish(
            aio_pika.Message(body=result.encode()),
            routing_key=routing_key,
        )
    await connection.close()

async def consumer(client, env):
    logger = DebugLogging(True).logger

    loop = asyncio.get_event_loop()
    connection = await aio_pika.connect_robust(
        "amqp://guest:guest@127.0.0.1/", loop=loop
    )
    queue_name = "download_forward"
 
    logger.debug('Telethon login')
    await client.start()

    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue(queue_name, auto_delete=True, durable=True)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    data = message.body.decode('utf-8').split('_')
                    chat_id, m_id, mime, forward = data

                    entity = await client.get_entity(int(env.FORWARD_CHANNEL))
                    chann_msg = await client.get_messages(entity, ids=int(forward))

                    filename = chann_msg.media.document.attributes[0].file_name
                    logger.debug('Received message <%d> file name <%s>' % (int(forward), filename))
                    media = chann_msg.media.document
                    path = os.path.abspath(
                        os.path.join(env.CONTENT_DIR, str(uuid4())[:8]+filename)
                    )
                    await client.download_media(media, file=path)
                    payload = f'{path}\n{mime}\n{chat_id}\n{m_id}'
                    logger.debug('Download complete, push %s' % payload)
                    await push(payload)

def main():
    env = Env()
    if not os.path.isdir(env.CONTENT_DIR):
        os.mkdir(env.CONTENT_DIR)

    client = TelegramClient('session', env.TELETHON_API_KEY, env.TELETHON_API_HASH)
    loop = asyncio.get_event_loop()
    loop.create_task(consumer(client, env))
    loop.run_forever()

if __name__ in '__main__':
    if os.name != 'nt':
        uvloop.install()
    try:
        main()
    except Exception as e:
        print(e)
