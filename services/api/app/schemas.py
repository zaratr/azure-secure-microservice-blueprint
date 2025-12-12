from datetime import datetime
from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    document_url: str = Field(..., description="Location of document to process")


class JobResponse(BaseModel):
    id: str
    status: str
    result_location: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
