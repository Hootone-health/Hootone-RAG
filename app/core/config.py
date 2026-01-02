# Settings (Pydantic BaseSettings)
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pydantic import Field

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
    AWS_ACCESS_KEY_ID: str = Field(..., env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str = Field(..., env="AWS_SECRET_ACCESS_KEY")
    AWS_S3_BUCKET_NAME: str = Field(..., env="AWS_S3_BUCKET_NAME")
    AWS_REGION: str = Field(..., env="AWS_REGION")
    
    # Valkey/Redis settings (optional, for external Valkey connection)
    VALKEY_PASSWORD: str = Field(..., env="VALKEY_PASSWORD")
    VALKEY_HOST: str = Field(..., env="VALKEY_HOST")
    VALKEY_PORT: int = Field(..., env="VALKEY_PORT")
    
    # Qdrant settings (optional, if authentication is enabled)
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_URL: Optional[str] = None
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
