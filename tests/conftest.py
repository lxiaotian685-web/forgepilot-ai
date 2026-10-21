from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.seed import seed_demo


@pytest.fixture()
def api():
    url = os.getenv("TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    if url.startswith("sqlite"):
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
        Base.metadata.create_all(engine)
    else:
        engine = create_engine(url, future=True)
        tables = ", ".join(
            table.name for table in reversed(Base.metadata.sorted_tables)
        )
        with engine.begin() as connection:
            connection.execute(
                text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE")
            )

    testing_session = sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False
    )
    with testing_session() as session:
        ids = seed_demo(session)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, ids, testing_session
    app.dependency_overrides.clear()
    engine.dispose()
