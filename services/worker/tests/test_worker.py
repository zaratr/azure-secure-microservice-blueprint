import pytest
from sqlalchemy import select

from app.main import process_job
from app.database import SessionLocal, init_db
from app.models import Job


@pytest.mark.asyncio
async def test_job_state_transitions(monkeypatch):
    await init_db()
    async with SessionLocal() as session:
        job = Job(id="test", input_payload='{"document_url": "http://example.com"}')
        session.add(job)
        await session.commit()
        await session.refresh(job)

        monkeypatch.setattr("app.main.upload_artifact", lambda job_id, content: "http://blob/test")
        await process_job({"job_id": job.id, "document_url": "http://example.com"}, session)
        result = await session.execute(select(Job).where(Job.id == job.id))
        persisted = result.scalar_one()
        assert persisted.status == "COMPLETED"
        assert persisted.result_location is not None
