from pydantic import PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    env: str = "dev"
    log_level: str = "INFO"
    database_url: PostgresDsn = PostgresDsn("postgresql+asyncpg://postgres:dev@localhost/setlist")
    echo_sql: bool = False
    jwt_secret: SecretStr = SecretStr("change-me-in-production-32-bytes!")
    jwt_access_ttl_hours: int = 24
    jwt_refresh_ttl_days: int = 7

    @field_validator("database_url", mode="before")
    @classmethod
    def coerce_asyncpg_scheme(cls, v: object) -> object:
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v
