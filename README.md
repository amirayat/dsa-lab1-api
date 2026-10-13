# dsa-lab1-api

FastAPI application for the DSA Lab 1 distributed image-analysis pipeline. Provides REST endpoints to submit images and query their processing status and results.

---

## What It Does

The API is the entry point of the system:

1. Receives a list of images from a client via HTTP multipart form.
2. Generates a UUID for each image.
3. Uploads each image to Azure Blob Storage as {image_id}.jpg.
4. Inserts one row per image into PostgreSQL with state = 'q1 Queued'.
5. Returns the request_id and image_ids to the client.
6. (Optional) Caller polls GET /status and GET /result to fetch progress and results.

Event Grid, Service Bus, and the Azure Function worker handle the rest asynchronously.

---

## Pipeline

Client -> [THIS API] -> Blob Storage -> Event Grid -> Service Bus
                                                          |
                                                          v
                                                  Azure Function (30s)
                                                          |
                                                          v
                                            Azure Face + Translator
                                                          |
                                                          v
                                                     PostgreSQL
                                                          |
                                                          v
                                          Client <- [THIS API] /status
                                          Client <- [THIS API] /result

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | / | Root info |
| GET | /health | Liveness check |
| GET | /db-check | PostgreSQL connectivity check |
| POST | /submit | Upload a batch of images |
| GET | /status/{request_id} | Aggregate + per-image status |
| GET | /result/{image_id} | Full detection result (with translations) |

Interactive documentation is available at /docs (Swagger UI).

---

## Request / Response Examples

### POST /submit

Request (multipart form):
- user_id: string
- files: list of image files

Response:
{
  "request_id": "8f3e1d2c-...",
  "image_ids": ["a4b5c6d7-...", "e8f9a0b1-..."],
  "status": "pending"
}

### GET /status/{request_id}

Response:
{
  "id": "8f3e1d2c-...",
  "user_id": "amir",
  "status": "done",
  "total": 2,
  "completed": 2,
  "failed": 0,
  "images": [
    { "id": "a4b5c6d7-...", "state": "q7 ResultsReady", "filename": "glasses.jpg" },
    { "id": "e8f9a0b1-...", "state": "q7 ResultsReady", "filename": "mask.jpg" }
  ]
}

### GET /result/{image_id}

Response:
{
  "id": "a4b5c6d7-...",
  "filename": "glasses.jpg",
  "state": "q7 ResultsReady",
  "result": [
    {
      "glasses": "Sunglasses",
      "glasses_ro": "Ochelari de soare",
      "mask": "noMask",
      "mask_ro": "Fara masca",
      "blur": "low",
      "blur_ro": "joasa",
      "exposure": "goodExposure",
      "exposure_ro": "bunaExpunere",
      "quality": "medium",
      "quality_ro": "Mediu"
    }
  ],
  "error": null
}

---

## Project Files

dsa-lab1-api/
  main.py                 FastAPI entry point
  requirements.txt        Python dependencies
  app/
    db.py                 asyncpg pool (lazy init)
    repository.py         DB queries
    schemas.py            Pydantic models
    blob_storage.py       Blob upload helper
  .github/workflows/      GitHub Actions deployment

---

## Environment Variables

PostgreSQL:
- POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD

Blob Storage:
- BLOB_CONNECTION_STRING, BLOB_CONTAINER_NAME

---

## Local Development

python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

Open http://localhost:8000/docs for the Swagger UI.

Secrets go in a local .env file (gitignored):

POSTGRES_HOST=...
POSTGRES_PORT=5432
POSTGRES_DB=facelab
POSTGRES_USER=pgadmin
POSTGRES_PASSWORD=...
BLOB_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
BLOB_CONTAINER_NAME=incoming-images

---

## Deploy

Automatic via GitHub Actions on push to main.

Azure App Service configuration:
- Runtime: Python 3.12
- Startup Command: gunicorn -k uvicorn.workers.UvicornWorker --preload --workers 1 --timeout 600 main:app
- Environment: SCM_DO_BUILD_DURING_DEPLOYMENT=true
- Environment: WEBSITES_PORT=8000

---

## Related Repositories

- dsa-lab1-worker-v2 — Azure Function worker (30s timer)
- dsa-lab1-grpc — gRPC server + client (Part 3)

---

## FSM States (from Part 0)

| State | Meaning |
|-------|---------|
| q1 Queued | Set by the API on submission |
| q2 Sending | Set by the worker |
| q4 SingleFaceDetected | One face found |
| q5 MultipleFacesDetected | Two or more faces |
| q6 NoFaceDetected | Zero faces (valid outcome) |
| q7 ResultsReady | Result saved |
| q9 Retry | Transient error |
| q10 Failed | Permanent error |

The images.state column stores the current FSM state of every image.

---

Laboratory work — Kaunas University of Technology, 2026.
