"""
Thread-local lazy-reconnect DB connection.

Each worker thread keeps one persistent connection. If the connection is
lost (idle timeout, server restart, etc.), it is automatically recreated on
the next call. This gives connection reuse without any borrow/return ceremony
— all callers just use get_db_connection() and put_db_connection() as before,
but put_db_connection() is now a no-op (the connection stays open for the
lifetime of the thread).
"""
import os
import threading
import logging
import psycopg2

# Force Cloud DB connection following user request
DB_CONNECTION_STRING = "postgresql://bar_admin:RABpass021819!@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"

_local = threading.local()


def _new_conn():
    conn = psycopg2.connect(DB_CONNECTION_STRING, connect_timeout=5)
    conn.autocommit = False
    return conn


def get_db_connection():
    """
    Return the thread-local connection, creating or reconnecting as needed.
    Callers do NOT need to close or return it — the connection persists for
    the lifetime of the worker thread.
    """
    conn = getattr(_local, "conn", None)
    if conn is None or conn.closed:
        logging.info("DB: opening new thread-local connection")
        _local.conn = _new_conn()
    else:
        # Quick liveness check — rolls back any previous failed transaction
        try:
            if conn.status == psycopg2.extensions.STATUS_IN_TRANSACTION:
                conn.rollback()
        except Exception:
            logging.warning("DB: dead connection detected, reconnecting")
            try:
                conn.close()
            except Exception:
                pass
            _local.conn = _new_conn()
    return _local.conn


def put_db_connection(conn):
    """
    No-op — the thread-local connection is kept alive for reuse.
    Only rolls back any uncommitted state so the next caller gets a clean tx.
    """
    try:
        if conn and not conn.closed:
            conn.rollback()
    except Exception:
        pass


class get_db_conn:
    """
    Optional context manager for callers that want RAII style:

        with get_db_conn() as conn:
            cur = conn.cursor(...)
    """
    def __enter__(self):
        self.conn = get_db_connection()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        put_db_connection(self.conn)
        return False
