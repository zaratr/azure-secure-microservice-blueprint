from functools import lru_cache
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    database_url: str = Field("sqlite+aiosqlite:///:memory:", env="DATABASE_URL")
    service_bus_connection: str | None = Field(default=None, env="SERVICE_BUS_CONNECTION")
    service_bus_queue: str = Field(default="jobs")
    otlp_endpoint: str | None = Field(default=None, env="OTLP_ENDPOINT")
    app_insights_connection_string: str | None = Field(default=None, env="APPINSIGHTS_CONNECTIONSTRING")
    rate_limit: str = Field(default="10/minute")
    azure_client_id: str | None = Field(default=None, env="AZURE_CLIENT_ID")

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
