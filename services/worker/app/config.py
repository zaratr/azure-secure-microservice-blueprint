from functools import lru_cache
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    database_url: str = Field("sqlite+aiosqlite:///:memory:", env="DATABASE_URL")
    service_bus_connection: str | None = Field(default=None, env="SERVICE_BUS_CONNECTION")
    service_bus_queue: str = Field(default="jobs")
    storage_account_url: str = Field("http://localhost:10000/devstoreaccount1", env="STORAGE_ACCOUNT_URL")
    storage_container: str = Field(default="artifacts")
    otlp_endpoint: str | None = Field(default=None, env="OTLP_ENDPOINT")
    azure_client_id: str | None = Field(default=None, env="AZURE_CLIENT_ID")

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
