"""Configuracao do MCP Server."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Caminho absoluto, derivado da localizacao deste arquivo — nao do cwd.
# Quando outro cliente MCP (Claude Code, Codex) lanca o servidor, ele o faz do
# diretorio dele: um `env_file=".env"` relativo simplesmente nao acha nada, e
# a configuracao volta ao default sem avisar ninguem.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_prefix="",
        extra="ignore",
    )

    store_api_base_url: str = Field(
        default="http://127.0.0.1:5000", alias="STORE_API_BASE_URL"
    )
    store_api_timeout_seconds: float = Field(
        default=5.0, gt=0, le=30, alias="STORE_API_TIMEOUT_SECONDS"
    )

    log_level: str = Field(default="INFO", alias="STORE_LOG_LEVEL")


settings = Settings()
