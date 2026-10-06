"""
DSA Lab 1 API — FastAPI entry point
Student: Amir Ayat, Internal Code: F3319, Variant: 7 (Azure Face)
"""
import os
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, HTTPException

db_pool: asyncpg.Pool = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: connect to PostgreSQL. Shutdown: close pool."""
    global db_pool
    db_pool = await asyncpg.create_pool(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        database=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        ssl=os.environ.get("POSTGRES_SSLMODE", "require"),
        min_size=1,
        max_size=5,
    )
    yield
    await db_pool.close()


app = FastAPI(title="DSA Lab 1 API", version="0.1.0", lifespan=lifespan)


@app.get("/")
def root():
    return {"service": "dsa-lab1-api", "status": "running", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/db-check")
async def db_check():
    """Verify PostgreSQL connection."""
    try:
        async with db_pool.acquire() as conn:
            version = await conn.fetchval("SELECT version()")
        return {"status": "connected", "postgres_version": version}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))