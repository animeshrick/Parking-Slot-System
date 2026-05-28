from pydantic_settings import BaseSettings
import os
from typing import Optional, List

class AppConfig(BaseSettings):
    APP_NAME: str = os.getenv("APP_NAME", "Async-Task-Queue")
    APP_ENV: str = os.getenv("APP_ENV", "local")
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", 8000))
    APP_DESCRIPTION: str = os.getenv("APP_DESCRIPTION", "NA")
    APP_VERSION: str = os.getenv("APP_VERSION", "0.0.0")
    API_VERSIONS: List[str] = []

    REDIS_HOST: Optional[str] = os.getenv("REDIS_HOST", "192.168.5.192")
    REDIS_PORT: Optional[int] = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB: Optional[int] = int(os.getenv("REDIS_DB", 0))
    REDIS_AUTH_TOKEN: Optional[str] = os.getenv("REDIS_AUTH_TOKEN") or None
    REDIS_SSL: bool = os.getenv("REDIS_SSL", "false").lower() == "true"

    # Billing — per-hour rates, snapshotted into each ticket on issue.
    RATE_CAR: int = int(os.getenv("RATE_CAR", 100))
    RATE_BIKE: int = int(os.getenv("RATE_BIKE", 50))
    RATE_TRUCK: int = int(os.getenv("RATE_TRUCK", 300))
    # Parking shorter than this is free.
    GRACE_PERIOD_MINUTES: int = int(os.getenv("GRACE_PERIOD_MINUTES", 15))

    TOTAL_SLOTS: int = int(os.getenv("TOTAL_SLOTS", 10))
    TOTAL_FLOORS: int = int(os.getenv("TOTAL_FLOORS", 1))
    
    MAX_TICKET_ISSUE_RETRIES: int = int(os.getenv("MAX_TICKET_ISSUE_RETRIES", 1))

    class Config:
        case_sensitive = True
        env_file = ".env"

appconfig = AppConfig()