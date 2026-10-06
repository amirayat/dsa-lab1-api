"""
DSA Lab 1 API — FastAPI entry point
Student: Amir Ayat, Internal Code: F3319, Variant: 7 (Azure Face)
"""
from typing import List
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, UploadFile, File, Form

from app.db import get_pool, close_pool
from app.blob_storage import upload_to_blob
from app.repository import (
    create_request,
    create_image,
    get_request,
    get_image,
)
from app.schemas import SubmitResponse, RequestStatus, ImageResult


app = FastAPI(
    title="DSA Lab 1 API",
    description="Distributed system with Azure Face (mask & glasses detection)",
    version="0.3.0",
)


@app.on_event("shutdown")
async def shutdown():
    await close_pool()


# ---------- Health ----------

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


# ---------- Submit ----------

@app.post("/submit", response_model=SubmitResponse)
async def submit(
    user_id: str = Form(...),
    files: List[UploadFile] = File(...),
):
    """
    Submit a list of images.

    For each image:
      1. Generate a UUID (used as image_id and blob_name)
      2. Upload to Blob Storage as {image_id}.jpg
      3. Insert a row in `images` with state = 'q1 Queued'
      4. Event Grid will auto-publish a message to Service Bus

    Returns:
      request_id + list of image_ids
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # 1. Create the request row
    request_id = await create_request(user_id=user_id, total=len(files))

    image_ids: list[UUID] = []

    for f in files:
        # 2. Generate a unique UUID for this image
        image_id = uuid4()
        blob_name = f"{image_id}.jpg"

        # 3. Read the uploaded bytes
        try:
            image_bytes = await f.read()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to read file {f.filename}: {e}")

        if not image_bytes:
            raise HTTPException(status_code=400, detail=f"Empty file: {f.filename}")

        # 4. Upload to Blob Storage
        try:
            blob_url = await upload_to_blob(
                blob_name=blob_name,
                data=image_bytes,
                content_type=f.content_type or "image/jpeg",
            )
        except Exception as e:
            # Rollback partial work is out of scope for the lab.
            # In production, use a saga pattern or compensating transactions.
            raise HTTPException(status_code=500, detail=f"Blob upload failed: {e}")

        # 5. Insert DB row
        await create_image(
            image_id=image_id,
            request_id=request_id,
            filename=f.filename or "unknown.jpg",   # display name
            blob_url=blob_url,                       # real Azure URL
            state="q1 Queued",
        )

        image_ids.append(image_id)

    return SubmitResponse(
        request_id=request_id,
        image_ids=image_ids,
        status="pending",
    )


# ---------- Status ----------

@app.get("/status/{request_id}", response_model=RequestStatus)
async def status(request_id: UUID):
    req = await get_request(request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")
    return req


# ---------- Result ----------

@app.get("/result/{image_id}", response_model=ImageResult)
async def result(image_id: UUID):
    img = await get_image(image_id)
    if img is None:
        raise HTTPException(status_code=404, detail="Image not found")

    return ImageResult(
        id=img["id"],
        filename=img["filename"],
        state=img["state"],
        result=img["result_json"],
        error=img["error"],
    )