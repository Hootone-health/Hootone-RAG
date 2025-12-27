# Settings (Pydantic BaseSettings)
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: str
    
    # JWT settings
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_HOURS: int = 1
    
    # Rate limiting settings
    RATE_LIMIT_REQUESTS: int = 5
    RATE_LIMIT_WINDOW_SECONDS: int = 60  # 1 minute
    
    # AWS S3 settings (optional, for future S3 service)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_S3_BUCKET_NAME: Optional[str] = None
    AWS_REGION: Optional[str] = None
    
    # Valkey/Redis settings (optional, for external Valkey connection)
    VALKEY_PASSWORD: Optional[str] = None
    VALKEY_HOST: Optional[str] = None
    VALKEY_PORT: Optional[int] = None
    
    # Qdrant settings (optional, if authentication is enabled)
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_URL: Optional[str] = None
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
