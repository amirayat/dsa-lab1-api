"""
DSA Lab 1 API — FastAPI entry point
Student: Amir Ayat, Internal Code: F3319, Variant: 7 (Azure Face)
"""
from fastapi import FastAPI

app = FastAPI(
    title="DSA Lab 1 API",
    description="Distributed system with Azure Face, Blob Storage, Service Bus, PostgreSQL",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "service": "dsa-lab1-api",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}