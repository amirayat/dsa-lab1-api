"""
DSA Lab 1 API — FastAPI entry point
Student: Amir Ayat, Internal Code: F3319, Variant: 7 (Azure Face)
"""
from typing import List
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.db import get_pool, close_pool
from app.repository import (
    create_request,
    create_image,
    get_request,
    get_image,
    update_image_state,
)
from app.schemas import SubmitResponse, RequestStatus, ImageResult


app = FastAPI(
    title="DSA Lab 1 API",
    description="Distributed system with Azure Face (mask & glasses detection)",
    version="0.2.0",
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
    For now, files are acknowledged but not stored (Blob upload comes next).
    Each image is inserted with state 'q1 Queued'.
    """
    request_id = await create_request(user_id=user_id, total=len(files))

    image_ids = []
    for f in files:
        # In this stage, we use the filename as blob_url placeholder.
        # Next step will upload to Blob Storage and use the real URL.
        blob_url = f"pending://{f.filename}"
        image_id = await create_image(
            request_id=request_id,
            filename=f.filename,
            blob_url=blob_url,
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