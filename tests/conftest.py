import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.crud.user import create_user
from app.deps import get_db
from app.main import app
from app.models.base import Base
from app.schemas.user import UserCreate

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def db_session():
    """
    Fixture tạo/xoá bảng trước/sau mỗi test và override dependency get_db.
    """
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
def client(db_session):
    """Fixture trả về TestClient(app)."""
    return TestClient(app)


@pytest.fixture
def test_user(db_session):
    """Fixture tạo một user mẫu trong database."""
    user_in = UserCreate(
        email="user1@example.com",
        password="password123",
        name="User One",
    )
    return create_user(db_session, user_in)


@pytest.fixture
def auth_headers(test_user):
    """Fixture trả về Authorization Bearer token headers cho test_user."""
    token = create_access_token(subject=test_user.id)
    return {"Authorization": f"Bearer {token}"}
