"""
Bounded PostgreSQL connection pool (thread-safe).

Replaces per-thread persistent connections so concurrent Azure Functions requests
cannot exhaust the server's max_connections limit.

Configure via DB_POOL_MIN_CONN / DB_POOL_MAX_CONN (defaults 2 / 15).
"""
import logging
import time
import psycopg2
import psycopg2.pool

from config import DB_CONNECTION_STRING, DB_POOL_MIN_CONN, DB_POOL_MAX_CONN

_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        if not DB_CONNECTION_STRING or not str(DB_CONNECTION_STRING).strip():
            raise RuntimeError(
                "Database not configured: set DB_CONNECTION_STRING (cloud Postgres) "
                "in Application Settings or api/local.settings.json."
            )
        minconn = DB_POOL_MIN_CONN
        maxconn = DB_POOL_MAX_CONN
        logging.info("DB: initializing ThreadedConnectionPool min=%s max=%s", minconn, maxconn)
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=minconn,
            maxconn=maxconn,
            dsn=str(DB_CONNECTION_STRING).strip(),
            connect_timeout=10,
        )
    return _pool


def get_db_connection(retries=20, delay=0.5):
    """Borrow a connection from the pool. Always pair with put_db_connection(conn)."""
    pool = _get_pool()
    for attempt in range(retries):
        try:
            conn = pool.getconn()
            try:
                conn.autocommit = False
            except Exception:
                pass
            return conn
        except psycopg2.pool.PoolError as e:
            if "exhausted" in str(e).lower() and attempt < retries - 1:
                logging.warning(f"DB pool exhausted. Retrying in {delay}s (Attempt {attempt+1}/{retries})")
                time.sleep(delay)
                continue
            raise


def put_db_connection(conn):
    """Return a connection to the pool after rollback."""
    if conn is None:
        return
    pool = _get_pool()
    try:
        if not conn.closed:
            conn.rollback()
    except Exception:
        logging.warning("DB: rollback before putconn failed; closing connection")
        try:
            pool.putconn(conn, close=True)
        except Exception as ex:
            logging.warning("DB: putconn(close=True) failed: %s", ex)
        return
    try:
        pool.putconn(conn)
    except Exception as ex:
        logging.warning("DB: putconn failed: %s", ex)


class get_db_conn:
    """Context manager: checkout from pool and return in __exit__."""

    def __enter__(self):
        self.conn = get_db_connection()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        put_db_connection(self.conn)
        return False
