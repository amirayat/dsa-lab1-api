"""
app/schemas.py
Pydantic models for API requests and responses.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SubmitResponse(BaseModel):
    request_id: UUID
    image_ids: list[UUID]
    status: str = "pending"


class ImageStatus(BaseModel):
    id: UUID
    filename: str
    state: str
    attempts: int
    created_at: datetime
    updated_at: datetime


class RequestStatus(BaseModel):
    id: UUID
    user_id: str
    status: str
    total: int
    completed: int
    failed: int
    created_at: datetime
    updated_at: datetime
    images: list[ImageStatus]


class ImageResult(BaseModel):
    id: UUID
    filename: str
    state: str
    result: Optional[dict] = None
    error: Optional[str] = None