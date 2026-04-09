from pathlib import Path

from mees_shared.settings import BaseAppSettings


class Settings(BaseAppSettings):
    db_host: str = "192.168.128.9"
    db_name: str = "splitwise"
    db_user: str = "finance"
    db_sslmode: str = "require"
    api_port: int = 8400

    cors_origins: list[str] = [
        "https://trips.mees.st",
        "http://localhost:5173",
    ]

    # Pipeline ingest authentication
    pipeline_ingest_secret: str = ""

    # Splitwise API (for tagger utility)
    splitwise_consumer_key: str = ""
    splitwise_consumer_secret: str = ""
    splitwise_api_key: str = ""

    model_config = {
        "env_file": str(Path(__file__).resolve().parent / ".env"),
        "env_file_encoding": "utf-8",
    }


settings = Settings()
