"""Application configuration.

This module exposes a single `Config` instance which loads settings from
environment variables (and an optional `.env` file). Use the `Config`
object to access runtime configuration such as database DSNs and secret
keys. Keep secrets (like `JWT_KEY`) out of source control and provide
them via environment variables or a secrets manager in production.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
   
    DATABASE_URL: str
    BREVO_API_KEY: str
    BREVO_EMAIL: str
    BREVO_SENDER_NAME: str
    JWT_KEY: str
    JWT_ALGORITHM: str
    REDIS_URL: str
  
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore", 
    )


Config = Settings()