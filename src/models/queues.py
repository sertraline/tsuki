from .basemodel import BaseModel


class QueueManager(BaseModel):

    def __init__(self, sql: 'PostgresInterface'):
        super().__init__()
        self.sql = sql

    async def _init_table(self):
        await self.sql.execute("""
            CREATE TABLE queues (
                queue_name VARCHAR NOT NULL DEFAULT '' PRIMARY KEY,
                queue_limit SMALLINT DEFAULT 5
            )
        """)
        await self.sql.execute("""
            CREATE TABLE workers (
                worker_id INT NOT NULL DEFAULT 0 PRIMARY KEY,
                queue_name VARCHAR,
                queue_start DATE NOT NULL DEFAULT CURRENT_DATE,
                CONSTRAINT belong_to_queue
                    FOREIGN KEY(queue_name)
                    REFERENCES queues(queue_name)
            )
        """)

    async def insert_queue(self, queue_name, queue_limit=5):
        await self.sql.execute("""
            INSERT INTO queues VALUES ($1, $2)
        """, queue_name, queue_limit)

    async def insert_worker(self, worker_id, queue_name):
        await self.sql.execute("""
            INSERT INTO workers (worker_id, queue_name) 
            VALUES ($1, $2)
        """, worker_id, queue_name)

    async def get_worker(self, worker_id):
        async with self.sql.pool.acquire() as conn:
            worker = await conn.fetch("""
                SELECT * FROM workers WHERE worker_id = $1
            """, worker_id)
        return worker

    async def delete_worker(self, worker_id):
        await self.sql.execute("""
            DELETE FROM workers WHERE worker_id = $1
        """, worker_id)
