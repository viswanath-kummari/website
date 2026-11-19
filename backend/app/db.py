import logging
from contextlib import contextmanager

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

from backend.app.config import Config

logger = logging.getLogger(__name__)
_connection_pool = None


def init_db_pool(minconn=1, maxconn=2):
    global _connection_pool
    if _connection_pool is None:
        try:
            if Config.DATABASE_URL:
                _connection_pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=minconn,
                    maxconn=maxconn,
                    dsn=Config.DATABASE_URL,
                    connect_timeout=10,
                    sslmode='require',
                )
            else:
                _connection_pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=minconn,
                    maxconn=maxconn,
                    host=Config.DB_HOST,
                    port=Config.DB_PORT,
                    dbname=Config.DB_NAME,
                    user=Config.DB_USER,
                    password=Config.DB_PASSWORD,
                    connect_timeout=10,
                    sslmode='require',
                )
            logger.info("Supabase PostgreSQL connection pool initialized.")
        except Exception as exc:
            logger.error("Failed to initialize database pool: %s", exc)
            raise
    return _connection_pool


def get_pool():
    global _connection_pool
    if _connection_pool is None:
        init_db_pool()
    return _connection_pool


@contextmanager
def get_db_connection():
    pool_instance = get_pool()
    conn = pool_instance.getconn()
    try:
        yield conn
    finally:
        pool_instance.putconn(conn)


@contextmanager
def get_db_cursor(commit=False):
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            yield cursor
            if commit:
                conn.commit()
        except Exception:
            conn.rollback()
            logger.exception("Database operation failed, rolled back.")
            raise
        finally:
            cursor.close()


def query_one(sql, params=None):
    with get_db_cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchone()


def query_all(sql, params=None):
    with get_db_cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()


def execute(sql, params=None, commit=True):
    with get_db_cursor(commit=commit) as cur:
        cur.execute(sql, params or ())
        return cur.rowcount


def execute_returning(sql, params=None, commit=True):
    with get_db_cursor(commit=commit) as cur:
        cur.execute(sql, params or ())
        return cur.fetchone()
