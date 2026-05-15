from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    turso_database_url: str = ""
    turso_auth_token: str = ""
    local_db_path: str = "atleta.db"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
