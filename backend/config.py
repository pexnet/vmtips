"""
Configuration module for the VMTips backend.
All settings are loaded from environment variables with sensible defaults.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./vmtips.db"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 168
    admin_email: str = "admin@example.com"
    admin_password: str = "admin"
    world_cup_json_url: str = "https://worldcupjson.net/matches"
    openfootball_url: str = (
        "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
    )
    sync_source: str = "openfootball"   # "worldcupjson" | "openfootball"
    auto_sync_enabled: bool = False       # set AUTO_SYNC_ENABLED=true in prod once tournament starts
    auto_sync_interval_minutes: int = 5   # how often auto-sync runs when enabled
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    environment: str = "development"
    allow_public_registration: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
