from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongodb_url: str = "mongodb://localhost:27017"
    database_name: str = "qr_platform"
    secret_key: str = "changeme-at-least-32-chars-long!!"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7 days
    base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"


settings = Settings()
