"""
DSA Lab 1 API — FastAPI entry point
"""
import os
import ssl
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, HTTPException

db_pool: asyncpg.Pool = None


def build_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


async def get_pool() -> asyncpg.Pool:
    """Lazily create the pool on first use — survives gunicorn forking."""
    global db_pool
    if db_pool is None:
        db_pool = await asyncpg.create_pool(
            host=os.environ["POSTGRES_HOST"],
            port=int(os.environ.get("POSTGRES_PORT", "5432")),
            database=os.environ["POSTGRES_DB"],
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
            ssl=build_ssl_context(),
            min_size=1,
            max_size=5,
        )
    return db_pool


app = FastAPI(title="DSA Lab 1 API", version="0.1.0")


@app.get("/")
def root():
    return {"service": "dsa-lab1-api", "status": "running", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/db-check")
async def db_check():
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            version = await conn.fetchval("SELECT version()")
        return {"status": "connected", "postgres_version": version}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))