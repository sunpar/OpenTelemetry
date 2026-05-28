from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    auth_db_path: str = Field(
        default="/data/auth-api.sqlite3",
        validation_alias=AliasChoices("AUTH_API_DB_PATH", "AUTH_DB_PATH", "auth_db_path"),
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)
