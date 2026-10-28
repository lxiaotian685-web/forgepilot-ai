from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+pysqlite:///./forgepilot.db")


class Base(DeclarativeBase):
    pass


def create_db_engine(url: str) -> Engine:
    if os.getenv("APP_ENV", "development").lower() == "production" and not url.startswith(
        "postgresql"
    ):
        raise RuntimeError("生产环境必须配置 PostgreSQL DATABASE_URL")
    kwargs: dict[str, object] = {"future": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    elif url.startswith("postgresql"):
        kwargs["pool_pre_ping"] = True
    return create_engine(url, **kwargs)


_engine: Engine | None = None
_session_factory: sessionmaker | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_db_engine(DATABASE_URL)
    return _engine


def get_sessionmaker() -> sessionmaker:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(), autoflush=False, expire_on_commit=False
        )
    return _session_factory


def get_db() -> Generator[Session, None, None]:
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()
