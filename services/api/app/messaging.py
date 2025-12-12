import json
from azure.identity import DefaultAzureCredential
from azure.servicebus.aio import ServiceBusClient
from azure.servicebus import ServiceBusMessage

from .config import get_settings


settings = get_settings()


class QueueClient:
    def __init__(self):
        self._credential = None
        if settings.service_bus_connection:
            self._connection = settings.service_bus_connection
        else:
            self._connection = None
            self._credential = DefaultAzureCredential(client_id=settings.azure_client_id)

    async def send_job(self, payload: dict) -> None:
        if self._connection:
            client = ServiceBusClient.from_connection_string(self._connection)
        else:
            client = ServiceBusClient(
                fully_qualified_namespace=payload.get("namespace"),
                credential=self._credential,
            )
        async with client:
            sender = client.get_queue_sender(queue_name=settings.service_bus_queue)
            async with sender:
                message = ServiceBusMessage(json.dumps(payload))
                await sender.send_messages(message)
