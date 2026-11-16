"""Shared pytest fixtures.

Each test gets an isolated in-memory SQLite database.  The FastAPI dependency is
overridden so no test touches the developer's local NetPulse database.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - register models on Base.metadata
from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.models import Device


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True
    )
    session = testing_session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def device(db_session: Session) -> Device:
    record = Device(ip_address="192.168.1.10", hostname="demo-device", mac_address="aa:bb:cc:dd:ee:ff")
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record
