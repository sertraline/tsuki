from telethon.sync import TelegramClient, events
from telethon.tl.types import InputPeerChat
from dataclasses import dataclass
from uuid import uuid4
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


def main():
    env = Env()
    if not os.path.isdir(env.CONTENT_DIR):
        os.mkdir(env.CONTENT_DIR)
    with TelegramClient('session', env.TELETHON_API_KEY, env.TELETHON_API_HASH) as client:
        @client.on(events.NewMessage(chats=int(env.FORWARD_CHANNEL)))
        async def handler(event):
            print(event)
            # fwd_from=MessageFwdHeader(date=datetime.datetime(2021, 8, 30, 6, 43, 40, tzinfo=datetime.timezone.utc)
            try:
                stamp = event.date
            except AttributeError as e:
                print(e)
                return
            media = event.media.document
            print('connect')
            connection = await aio_pika.connect_robust(
                "amqp://guest:guest@127.0.0.1/"
            )
            print('connected')
            queue_name = "download_forward"

            attempts = 60
            while attempts:
                async with connection:
                    channel = await connection.channel()
                    queue = await channel.declare_queue(queue_name, auto_delete=True)

                    print('iter')
                    async with queue.iterator() as queue_iter:
                        async for message in queue_iter:
                            print('message')
                            async with message.process():
                                data = message.body.decode('utf-8').split('_')
                                chat_id, m_id, mime, forward = data
                                forward = datetime.datetime.utcfromtimestamp(int(forward))
                                forward = forward.replace(tzinfo=datetime.timezone.utc)
                                print(forward, stamp)
                                if forward == stamp:
                                    print('Received message')
                                    filename = event.media.document.attributes[0].file_name
                                    path = os.path.abspath(
                                        os.path.join(env.CONTENT_DIR, str(uuid4())[:8]+filename)
                                    )
                                    await client.download_media(media, file=path)
                                    payload = f'{path}\n{mime}\n{chat_id}\n{m_id}'
                                    print('Download complete, push %s' % payload)
                                    await push(payload)
                                else:
                                    await message.reject(requeue=True)
                await asyncio.sleep(2)
                attempts -= 1

        InputPeerChat(int(env.FORWARD_CHANNEL))
        client.run_until_disconnected()


if __name__ in '__main__':
    if os.name != 'nt':
        uvloop.install()
    main()