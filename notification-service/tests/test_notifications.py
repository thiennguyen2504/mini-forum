import os
import sys

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db import Base, get_db
from app.main import app
from app.models import Notification

engine = create_engine(
    "sqlite:///:memory:",
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield db
    db.close()
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check_degraded_when_kafka_down(client):
    # Khi Kafka chưa chạy trong unit test, probe trả 503 với kafka: error
    res = client.get("/health")
    assert res.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    data = res.json()
    assert data["status"] == "error"
    assert data["db"] == "ok"
    assert data["kafka"] == "error"


def test_health_check_ok(client, monkeypatch):
    # Giả lập khi Kafka consumer đang hoạt động bình thường
    monkeypatch.setattr("app.main.is_consumer_running", lambda: True)
    res = client.get("/health")
    assert res.status_code == status.HTTP_200_OK
    assert res.json() == {"status": "ok", "db": "ok", "kafka": "ok"}


def test_get_notifications_empty(client):
    res = client.get("/notifications/123")
    assert res.status_code == status.HTTP_200_OK
    assert res.json() == []


def test_get_notifications_list(client, db_session):
    notif1 = Notification(user_id=10, message="Message 1", is_read=False)
    notif2 = Notification(user_id=10, message="Message 2", is_read=True)
    notif_other = Notification(user_id=99, message="Other user", is_read=False)
    db_session.add_all([notif1, notif2, notif_other])
    db_session.commit()

    res = client.get("/notifications/10")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert len(data) == 2
    messages = [item["message"] for item in data]
    assert "Message 1" in messages
    assert "Message 2" in messages
    assert all(item["user_id"] == 10 for item in data)
