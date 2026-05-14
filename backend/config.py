"""
Configuration module for the VMTips backend.
All settings are loaded from environment variables with sensible defaults.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./vmtips.db"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 168
    admin_email: str = "admin@example.com"
    world_cup_json_url: str = "https://worldcupjson.net/matches"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    class Config:
        env_file = ".env"


settings = Settings()
