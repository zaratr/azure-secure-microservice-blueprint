import asyncio
import json
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
import uuid

from .config import get_settings
from .database import get_db, engine
from .logging_setup import configure_logging, get_logger
from .messaging import QueueClient
from .models import Base, Job
from .schemas import JobCreate, JobResponse

settings = get_settings()
configure_logging()
logger = get_logger(__name__)
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("x-correlation-id", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["x-correlation-id"] = correlation_id
        return response


app = FastAPI(title="Secure Blueprint API")
app.state.queue_client = QueueClient()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(CorrelationIdMiddleware)
app.state.limiter = limiter


@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("startup complete")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit)
async def create_job(
    job: JobCreate, db: Annotated[AsyncSession, Depends(get_db)], request: Request
):
    new_job = Job(input_payload=json.dumps(job.model_dump()))
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)

    payload = {"job_id": new_job.id, "document_url": job.document_url}
    try:
        await app.state.queue_client.send_job(payload)
    except Exception as exc:  # noqa: BLE001
        logger.error("failed to enqueue", exc_info=exc)
        raise HTTPException(status_code=500, detail="Failed to enqueue job") from exc

    logger.info("job created", job_id=new_job.id, correlation_id=request.state.correlation_id)
    return new_job


@app.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, db: Annotated[AsyncSession, Depends(get_db)], request: Request):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    logger.info("job retrieved", job_id=job_id, correlation_id=request.state.correlation_id)
    return job


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):  # noqa: ANN201
    logger.error("unhandled error", exc_info=exc, correlation_id=request.state.correlation_id)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
