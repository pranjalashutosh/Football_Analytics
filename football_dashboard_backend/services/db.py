# services/db.py
import os
from contextlib import contextmanager

import pandas as pd
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from dotenv import load_dotenv

# ------------------------------------------------------------
# 1. Load environment variables (.env)
# ------------------------------------------------------------
load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME", "football_db")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

# ------------------------------------------------------------
# 2. Initialise (or reuse) a connection pool
# ------------------------------------------------------------
_pool: SimpleConnectionPool | None = None


def init_pool(minconn: int = 1, maxconn: int = 5):
    global _pool
    if _pool is None:
        _pool = SimpleConnectionPool(
            minconn,
            maxconn,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
        )
    return _pool


init_pool()

# ------------------------------------------------------------
# 3. Context manager to borrow/return a connection
# ------------------------------------------------------------
@contextmanager
def get_conn():
    """
    Usage:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    """
    conn = _pool.getconn()
    try:
        yield conn
    finally:
        _pool.putconn(conn)


# ------------------------------------------------------------
# 4. Helper to run a SELECT and get a DataFrame
# ------------------------------------------------------------
def fetch_df(sql: str, params: tuple | dict | None = None) -> pd.DataFrame:
    """Run a read‑only query and return a pandas DataFrame."""
    with get_conn() as conn:
        df = pd.read_sql_query(sql, conn, params=params)
    return df


# ------------------------------------------------------------
# 5. Helper to run INSERT/UPDATE/DELETE
# ------------------------------------------------------------
def execute(sql: str, params: tuple | dict | None = None) -> int:
    """Execute write query and return number of rows affected."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            affected = cur.rowcount
        conn.commit()
    return affected
