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

    apple_bundle_id: str = "com.setlistpicker.app"
    apple_jwks_url: str = "https://appleid.apple.com/auth/keys"

    google_client_id: str = "replace-with-google-client-id"
    google_jwks_url: str = "https://www.googleapis.com/oauth2/v3/certs"

    admin_token: SecretStr = SecretStr("test-admin-token")

    spotify_client_id: str = ""
    spotify_client_secret: SecretStr = SecretStr("")
    lastfm_api_key: SecretStr = SecretStr("")
    artist_cache_ttl_seconds: int = 604800  # 7 days
    artist_max_backoff_hours: int = 24

    # Apple Music — developer JWT credentials
    apple_music_team_id: str = ""
    apple_music_key_id: str = ""
    apple_music_private_key_base64: SecretStr = SecretStr("")
    # Controls which source is tried first for artist detail enrichment.
    # Values: "apple_music" | "spotify" | "both"
    artist_source: str = "apple_music"

    cors_origins: list[str] = []
    trusted_hosts: list[str] = ["*"]

    @field_validator("database_url", mode="before")
    @classmethod
    def coerce_asyncpg_scheme(cls, v: object) -> object:
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v
