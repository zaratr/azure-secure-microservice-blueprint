import asyncio
import json
from datetime import datetime
from azure.identity import DefaultAzureCredential
from azure.servicebus.aio import ServiceBusClient
from azure.storage.blob.aio import BlobServiceClient
from sqlalchemy import select, update
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import get_settings
from .database import SessionLocal, init_db
from .logging_setup import configure_logging, get_logger
from .models import Job

settings = get_settings()
configure_logging()
logger = get_logger(__name__)


async def process_job(message_body: dict, session):
    job_id = message_body["job_id"]
    await session.execute(update(Job).where(Job.id == job_id).values(status="PROCESSING"))
    await session.commit()

    artifact_text = f"Processed document {message_body['document_url']} at {datetime.utcnow().isoformat()}"
    blob_url = await upload_artifact(job_id, artifact_text)

    await session.execute(
        update(Job)
        .where(Job.id == job_id)
        .values(status="COMPLETED", result_location=blob_url, updated_at=datetime.utcnow())
    )
    await session.commit()
    logger.info("job completed", job_id=job_id, artifact=blob_url)


@retry(wait=wait_exponential(min=1, max=8), stop=stop_after_attempt(3))
async def upload_artifact(job_id: str, content: str) -> str:
    credential = DefaultAzureCredential(client_id=settings.azure_client_id)
    blob_service = BlobServiceClient(account_url=settings.storage_account_url, credential=credential)
    container_client = blob_service.get_container_client(settings.storage_container)
    await container_client.create_container(exist_ok=True)
    blob_client = container_client.get_blob_client(f"{job_id}.txt")
    await blob_client.upload_blob(content, overwrite=True)
    return blob_client.url


async def handle_messages_service_bus():
    credential = None if settings.service_bus_connection else DefaultAzureCredential(client_id=settings.azure_client_id)
    if settings.service_bus_connection:
        bus_client = ServiceBusClient.from_connection_string(settings.service_bus_connection)
    else:
        raise RuntimeError("Service Bus connection required for cloud run")

    async with bus_client:
        receiver = bus_client.get_queue_receiver(queue_name=settings.service_bus_queue, max_wait_time=5)
        async with receiver:
            async for msg in receiver:
                body = json.loads(str(msg))
                async with SessionLocal() as session:
                    try:
                        await process_job(body, session)
                        await receiver.complete_message(msg)
                    except Exception as exc:  # noqa: BLE001
                        logger.error("processing failed", exc_info=exc)
                        await receiver.abandon_message(msg)


async def handle_messages_local_poll():
    async with SessionLocal() as session:
        result = await session.execute(select(Job).where(Job.status == "PENDING"))
        for job in result.scalars():
            await process_job({"job_id": job.id, "document_url": json.loads(job.input_payload)["document_url"]}, session)


async def main():
    await init_db()
    while True:
        if settings.service_bus_connection:
            await handle_messages_service_bus()
        else:
            await handle_messages_local_poll()
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
