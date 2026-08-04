import traceback
from contextlib import asynccontextmanager
from databases import Database
from databases.core import Connection
from loguru import logger as log
from app.include.config import config


class DBConnPool:
    db_conn = None

    async def init_db(self):
        try:
            self.db_conn = Database(
                url=config.DB_URL,
                min_size=config.DB_MIN_CONNECTIONS,
                max_size=config.DB_MAX_CONNECTIONS,
            )
            await self.db_conn.connect()
        except Exception as e:
            log.error(f"(init_db) database not available! Exception: {repr(e)}, {traceback.format_exc()}")
            raise

    @property
    def database(self):
        return self.db_conn

    async def close_db(self):
        try:
            log.info(f"(close_db) Close pool...")
            await self.db_conn.disconnect()
        except Exception as e:
            log.error(f"(close_db) Exception: {repr(e)}, {traceback.format_exc()}")
            raise

    @asynccontextmanager
    async def get_connection(self) -> Connection:
        async with self.db_conn.connection() as connection:
            yield connection


db_pool = DBConnPool()