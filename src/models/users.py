import asyncio
from .basemodel import BaseModel
from datetime import datetime


class UserManager(BaseModel):

    def __init__(self, sql: 'PostgresInterface'):
        super().__init__()
        self.sql = sql

    async def _init_table(self):
        await self.sql.execute("""
        CREATE TABLE users (
            user_id INTEGER PRIMARY KEY,
            first_name VARCHAR NOT NULL DEFAULT '',
            last_name VARCHAR NOT NULL DEFAULT '',
            username VARCHAR NOT NULL DEFAULT ''
        )
        """)

    async def user_entry(self, user_id, first_name, last_name, username):
        if not last_name:
            last_name = ''
        await self.sql.execute("""
            INSERT INTO users(user_id, first_name, last_name, username) 
            VALUES($1, $2, $3, $4) 
            ON CONFLICT (user_id) DO UPDATE SET
            first_name = $2, last_name = $3, username = $4
        """, user_id, first_name, last_name, username)

    async def get_user(self, user_id):
        async with self.sql.pool.acquire() as conn:
            user = await conn.fetchrow("""
                SELECT *  
                FROM users WHERE user_id = $1
            """, user_id)
        if not user:
            return

        user_data = dict(user)
        user = User(self.sql, user_data)
        return user


class User:

    def __init__(self, sql: 'PostgresInterface', data: dict):
        super().__init__()
        self.sql = sql
        self.loop = asyncio.get_event_loop()
        self.user_id = data['user_id']
        self.first_name = data['first_name']
        self.last_name = data['last_name']
        self._username = data['username']

    async def set_column(self, col, value):
        await self.sql.execute(f"""
            UPDATE users SET {col} = $1 WHERE user_id = $2
        """, value, self.user_id)

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, value: str):
        self.loop.create_task(self.set_column('username', value))
        self._username = value
