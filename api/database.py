import os
import logging
from psycopg_pool import AsyncConnectionPool

# Global Database Pool
db_pool = None

async def get_db_pool():
    global db_pool
    if db_pool is None:
        try:
            db_pool = AsyncConnectionPool(
                conninfo=os.environ["DB_CONNECTION_STRING"],
                min_size=1,
                max_size=10,
                open=False # Don't open immediately
            )
            await db_pool.open()
        except Exception as e:
            logging.error(f"Failed to create DB pool: {e}")
            raise e
    return db_pool
