from pydantic_settings import SettingsConfigDict, BaseSettings


class Settings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1"]

    ELASTICSEARCH_HOST: str = "localhost"
    ELASTICSEARCH_PORT: int = 9200

    PROFILING_ENABLED: bool = False

    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "password"
    MINIO_BUCKET: str = "screenshots"
    MINIO_SECURE: bool = False

    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@backloggd.local"
    SMTP_ENABLED: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}"

    @property
    def elasticsearch_url(self) -> str:
        return f"http://{self.ELASTICSEARCH_HOST}:{self.ELASTICSEARCH_PORT}"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def minio_url(self) -> str:
        protocol = "https" if self.MINIO_SECURE else "http"
        return f"{protocol}://{self.MINIO_ENDPOINT}"


settings = Settings()
