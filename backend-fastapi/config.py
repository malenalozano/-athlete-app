import json
import os
from pydantic_settings import BaseSettings


def _parse_cors(v: str | list) -> list[str]:
    if isinstance(v, list):
        return v
    try:
        parsed = json.loads(v)
        if isinstance(parsed, list):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    return [s.strip() for s in v.split(",") if s.strip()]


class Settings(BaseSettings):
    turso_database_url: str = ""
    turso_auth_token: str = ""
    local_db_path: str = "atleta.db"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def __init__(self, **data):
        raw = os.environ.get("CORS_ORIGINS", "")
        if raw:
            data.setdefault("cors_origins", _parse_cors(raw))
        super().__init__(**data)


settings = Settings()
