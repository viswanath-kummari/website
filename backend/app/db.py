import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import logging
from backend.app.config import Config

logger = logging.getLogger(__name__)

# Connection pool instance
_connection_pool = None

def init_db_pool(minconn=1, maxconn=20):
    global _connection_pool
    if _connection_pool is None:
        try:
            _connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=minconn,
                maxconn=maxconn,
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                dbname=Config.DB_NAME,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                connect_timeout=10,
                sslmode='require'
            )
            logger.info("Supabase PostgreSQL connection pool initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise e
    return _connection_pool

def get_pool():
    global _connection_pool
    if _connection_pool is None:
        init_db_pool()
    return _connection_pool

@contextmanager
def get_db_connection():
    """Context manager for obtaining a database connection from the pool."""
    pool_instance = get_pool()
    conn = pool_instance.getconn()
    try:
        yield conn
    finally:
        pool_instance.putconn(conn)

@contextmanager
def get_db_cursor(commit=False):
    """
    Context manager for obtaining a cursor with RealDictCursor.
    If commit=True, automatically commits on successful block exit or rolls back on exception.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            yield cursor
            if commit:
                conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database operation failed, rolled back: {e}")
            raise e
        finally:
            cursor.close()

def query_one(sql, params=None):
    """Execute a SELECT query and return a single row as dict."""
    with get_db_cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchone()

def query_all(sql, params=None):
    """Execute a SELECT query and return all rows as list of dicts."""
    with get_db_cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()

def execute(sql, params=None, commit=True):
    """Execute an INSERT/UPDATE/DELETE query and optionally commit."""
    with get_db_cursor(commit=commit) as cur:
        cur.execute(sql, params or ())
        return cur.rowcount

def execute_returning(sql, params=None, commit=True):
    """Execute an INSERT/UPDATE/DELETE with RETURNING clause and return the row."""
    with get_db_cursor(commit=commit) as cur:
        cur.execute(sql, params or ())
        return cur.fetchone()
