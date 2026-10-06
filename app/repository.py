"""
app/repository.py
Database queries for requests and images.
"""
from typing import Optional
from uuid import UUID

import asyncpg
import json

from app.db import get_pool


# ---------- requests ----------

async def create_request(user_id: str, total: int) -> UUID:
    """Insert a new request row and return its ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO requests (user_id, total, status)
            VALUES ($1, $2, 'pending')
            RETURNING id
            """,
            user_id, total,
        )
    return row["id"]


async def get_request(request_id: UUID) -> Optional[dict]:
    """Fetch a request row with its images (aggregated status)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        req = await conn.fetchrow(
            "SELECT * FROM requests WHERE id = $1", request_id,
        )
        if req is None:
            return None

        images = await conn.fetch(
            """
            SELECT id, filename, state, attempts, created_at, updated_at
            FROM images
            WHERE request_id = $1
            ORDER BY created_at
            """,
            request_id,
        )

    return {
        "id": req["id"],
        "user_id": req["user_id"],
        "status": req["status"],
        "total": req["total"],
        "completed": req["completed"],
        "failed": req["failed"],
        "created_at": req["created_at"],
        "updated_at": req["updated_at"],
        "images": [dict(img) for img in images],
    }


async def increment_completed(request_id: UUID, failed: bool = False) -> None:
    """Increment completed (or failed) counter and refresh status."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if failed:
            await conn.execute(
                """
                UPDATE requests
                SET completed = completed + 1,
                    failed    = failed + 1,
                    status    = CASE
                                    WHEN completed + 1 >= total THEN 'done'
                                    ELSE status
                                END
                WHERE id = $1
                """,
                request_id,
            )
        else:
            await conn.execute(
                """
                UPDATE requests
                SET completed = completed + 1,
                    status    = CASE
                                    WHEN completed + 1 >= total THEN 'done'
                                    ELSE status
                                END
                WHERE id = $1
                """,
                request_id,
            )


# ---------- images ----------

async def create_image(
    image_id: UUID,                # ← now required
    request_id: UUID,
    filename: str,
    blob_url: str,
    state: str = "q1 Queued",
) -> UUID:
    """Insert an image row with an explicit image_id."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO images (id, request_id, filename, blob_url, state)
            VALUES ($1, $2, $3, $4, $5)
            """,
            image_id, request_id, filename, blob_url, state,
        )
    return image_id


async def get_image(image_id: UUID) -> Optional[dict]:
    """Fetch a single image row; parse result_json if present."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM images WHERE id = $1", image_id,
        )
    if not row:
        return None

    img = dict(row)
    # asyncpg returns JSONB as a string by default — decode it here
    if isinstance(img.get("result_json"), str):
        try:
            img["result_json"] = json.loads(img["result_json"])
        except (json.JSONDecodeError, TypeError):
            img["result_json"] = None
    return img


async def update_image_state(
    image_id: UUID,
    state: str,
    result_json: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    """Update image state and optionally set result/error."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE images
            SET state       = $2,
                result_json = COALESCE($3::jsonb, result_json),
                error       = COALESCE($3, error)
            WHERE id = $1
            """,
            image_id, state, result_json, error,
        )