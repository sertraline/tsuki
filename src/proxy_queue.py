import asyncio
import os
from random import choice


class ProxyQueue(asyncio.Queue):
    def shuffle(self):
        import random
        random.shuffle(self._queue)


async def init_queue(queue):
    ua_list = []
    with open(os.path.join('src', 'static', 'ua'), 'r') as f:
        for line in f:
            ua_list.append(line.strip())
    if queue.empty():
        with open(os.path.join('src', 'static', 'proxies.txt'), 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                await queue.put(['http://' + line.strip(), choice(ua_list)])
    return queue.shuffle()
