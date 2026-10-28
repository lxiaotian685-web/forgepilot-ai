from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.db import Base, create_db_engine
from app.main import readiness_check
from app.models import Device, Organization, WorkOrder
from app.seed import seed_demo


def test_production_requires_postgresql(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError, match="PostgreSQL DATABASE_URL"):
        create_db_engine("sqlite+pysqlite:///:memory:")


def test_sqlite_demo_data_survives_new_database_connection(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    db_file = tmp_path / "business.db"
    url = f"sqlite+pysqlite:///{db_file.as_posix()}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_demo(session)
    engine.dispose()

    restarted = create_engine(url)
    with Session(restarted) as session:
        assert session.scalar(select(Organization).where(Organization.code == "demo-org"))
        assert session.scalar(select(Device).where(Device.code == "AC-07"))
        assert session.scalar(select(WorkOrder).where(WorkOrder.code == "WO-20250518-01"))
    restarted.dispose()


def test_readiness_requires_a_database_query():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with Session(engine) as session:
        assert readiness_check(session) == {"status": "ready", "database": "ok"}
    engine.dispose()

    class OfflineSession:
        def execute(self, _statement):
            raise OperationalError("SELECT 1", {}, RuntimeError("offline"))

    with pytest.raises(HTTPException) as failure:
        readiness_check(OfflineSession())
    assert failure.value.status_code == 503


