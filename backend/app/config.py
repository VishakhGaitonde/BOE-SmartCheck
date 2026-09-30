from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    boe_username: str
    boe_password_hash: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 120
    database_url: str = "sqlite:///./smart_boe.db"
    llm_api_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()