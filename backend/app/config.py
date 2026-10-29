from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    boe_username: str
    boe_password_hash: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 120
    database_url: str = "sqlite:///./smart_boe.db"
    llm_api_key: str = ""
    allowed_origins: str = "http://localhost:5173"  # comma-separated list

    class Config:
        env_file = BASE_DIR / ".env"


settings = Settings()

ALLOWED_ORIGINS_LIST = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]