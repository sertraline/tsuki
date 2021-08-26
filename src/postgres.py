import asyncpg
import asyncio


class PostgresInterface:

    def __init__(self, debug):
        self.debug = debug
        self.pool = None
        self.init_db()

    def init_db(self):
        loop = asyncio.get_event_loop()
        self.pool = loop.run_until_complete(asyncpg.create_pool('postgresql://tsuki:tsuki@localhost/bot'))
        self.debug("CONNECT")

    async def execute(self, query, *args):
        self.debug("%s %s" % (query, str(args)))
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetchrow(self, query, *args):
        self.debug("%s %s" % (query, str(args)))
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
