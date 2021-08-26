from .basemodel import BaseModel
import asyncpg


class FileScan(BaseModel):

    def __init__(self, sql: 'PostgresInterface'):
        super().__init__()
        self.sql = sql

    async def _init_table(self):
        await self.sql.execute("""
            CREATE TABLE scans (
                sha256 VARCHAR NOT NULL DEFAULT '' PRIMARY KEY,
                scan_result TEXT DEFAULT ''
            )
        """)

    async def insert_scan(self, sha256, scan_result):
        await self.sql.execute("""
            INSERT INTO scans VALUES ($1, $2)
        """, sha256, scan_result)

    async def get_scan(self, sha256):
        return await self.sql.fetchrow("""
            SELECT * FROM scans WHERE sha256 = $1
        """, sha256)

    async def delete_scan(self, sha256):
        await self.sql.execute("""
            DELETE FROM scans WHERE sha256 = $1
        """, sha256)
