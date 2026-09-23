from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    APP_NAME: str = "Sistema de Estoque"
    APP_VERSION: str = "0.1.0"
    APP_ENV: Literal["development", "test", "production"] = "development"

    DATABASE_URL: str = "sqlite:///./stock.db"
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173"
    SECRET_KEY: str = "stock-default-jwt-secret-change-this-in-production-2026-secure"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"
    TRUSTED_HOSTS: str = "localhost,127.0.0.1,testserver"
    LOG_LEVEL: str = "INFO"
    METRICS_ENABLED: bool = True

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def trusted_hosts(self) -> list[str]:
        return [host.strip() for host in self.TRUSTED_HOSTS.split(",") if host.strip()]

    @model_validator(mode="after")
    def validate_production_settings(self):
        if self.APP_ENV != "production":
            return self
        if self.DATABASE_URL.startswith("sqlite"):
            raise ValueError("DATABASE_URL de producao deve usar PostgreSQL.")
        if self.SECRET_KEY.startswith(("stock-default-", "replace-with-")) or len(self.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY de producao deve ser exclusiva e ter pelo menos 32 caracteres.")
        if not self.cors_origins or "*" in self.cors_origins:
            raise ValueError("BACKEND_CORS_ORIGINS de producao deve listar origens explicitas.")
        if not self.trusted_hosts or "*" in self.trusted_hosts:
            raise ValueError("TRUSTED_HOSTS de producao deve listar hosts explicitos.")
        return self

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8"
    )


settings = Settings()
