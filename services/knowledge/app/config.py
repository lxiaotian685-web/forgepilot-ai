from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DEMO_DOCS_DIR = DATA_DIR / "demo_docs"
STORAGE_PATH = DATA_DIR / "knowledge_base.json"


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int, *, minimum: int | None = None) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} 必须是整数") from exc
    if minimum is not None and parsed < minimum:
        raise ValueError(f"{name} 不能小于 {minimum}")
    return parsed


def is_production() -> bool:
    return os.getenv("APP_ENV", "development").strip().lower() == "production"


def default_organization_id() -> str:
    return os.getenv("C_DEFAULT_ORGANIZATION_ID", "demo-org")


def auth_required() -> bool:
    return env_bool("C_REQUIRE_AUTH", True)


def identity_api_base_url() -> str:
    return os.getenv("C_IDENTITY_API_BASE_URL", "").strip().rstrip("/")


def ingest_enabled() -> bool:
    return env_bool("C_ENABLE_INGEST", False)


def max_upload_bytes() -> int:
    return env_int("MAX_UPLOAD_BYTES", 5_000_000, minimum=1)
