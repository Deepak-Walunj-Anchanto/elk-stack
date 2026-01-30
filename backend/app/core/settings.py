from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import List
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"

class Settings(BaseSettings):
    APP_NAME: str = Field(default="FastApi Backend", alias="APP_NAME")
    ENV: str = Field(default="Dev", alias="ENV")
    API_PREFIX: str = Field(default="/lms", alias="API_PREFIX")

    ALLOWED_ORIGINS: List[str] = Field(default=["http://localhost:5173"], alias="ALLOWED_ORIGINS")

    # Elasticsearch (API key auth; no basic auth for ES calls)
    ELASTICSEARCH_URL: str = Field(default="http://localhost:9200", alias="ELASTICSEARCH_URL")
    ELASTICSEARCH_API_KEY: str = Field(default="", alias="ELASTICSEARCH_API_KEY")

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_allowed_origins(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        )

settings = Settings()
