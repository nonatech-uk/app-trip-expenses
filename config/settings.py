from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Splitwise
    splitwise_consumer_key: str = ""
    splitwise_consumer_secret: str = ""
    splitwise_api_key: str = ""

    # Postgres — finance DB (for splitwise_tag.py)
    db_host: str = "192.168.128.9"
    db_port: int = 5432
    db_name: str = "finance"
    db_user: str = "finance"
    db_password: str = ""
    db_sslmode: str = "require"

    # Postgres — trips DB (for the web app)
    trips_db_name: str = "splitwise"

    # Web app
    app_port: int = 8001

    model_config = {
        "env_file": str(Path(__file__).resolve().parent / ".env"),
        "env_file_encoding": "utf-8",
    }

    @property
    def dsn(self) -> str:
        return (
            f"host={self.db_host} port={self.db_port} dbname={self.db_name} "
            f"user={self.db_user} password={self.db_password} sslmode={self.db_sslmode}"
        )

    @property
    def trips_dsn(self) -> str:
        return (
            f"host={self.db_host} port={self.db_port} dbname={self.trips_db_name} "
            f"user={self.db_user} password={self.db_password} sslmode={self.db_sslmode}"
        )


settings = Settings()
