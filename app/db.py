"""
app/db.py
PostgreSQL connection pool (lazy, gunicorn-safe).
"""
import os
import ssl
from typing import Optional

import asyncpg

_pool: Optional[asyncpg.Pool] = None


def _build_ssl_context() -> ssl.SSLContext:
    """Azure PostgreSQL requires SSL. Build a proper SSL context."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


async def get_pool() -> asyncpg.Pool:
    """Return the shared pool, creating it on first use."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=os.environ["POSTGRES_HOST"],
            port=int(os.environ.get("POSTGRES_PORT", "5432")),
            database=os.environ["POSTGRES_DB"],
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
            ssl=_build_ssl_context(),
            min_size=1,
            max_size=5,
        )
    return _pool


async def close_pool() -> None:
    """Close the pool on shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None