import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, User, get_db
from app.main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_user_registration_integration(client, db_session):
    response = client.post("/register", json={
        "username": "int_test_user",
        "password": "securepassword",
        "email": "int_test@example.com"
    })
    assert response.status_code == 201

    user_in_db = db_session.query(User).filter(User.username == "int_test_user").first()
    assert user_in_db is not None
    assert user_in_db.email == "int_test@example.com"


def test_register_same_email(client, db_session):
    for _ in range(3):
        response = client.post("/register", json={
            "username": "first",
            "password": "securepassword",
            "email": "int_test@example.com"
        })
        assert len(db_session.query(User).all()) == 1
    response = client.post("/register", json={
        "username": "second",
        "password": "securepassword2",
        "email": "second@example.com"
    })
    assert response.status_code == 201
    assert len(db_session.query(User).all()) == 2


def test_user_profile_update_integration(client, db_session):
    client.post("/register", json={
        "username": "profile_test",
        "password": "testpass",
        "email": "profile@test.com"
    })

    update_data = {
        "first_name": "New_name",
        "last_name": "Test",
        "mail": "updated@test.com"
    }
    response = client.put("/profile", json=update_data, params={"username": "profile_test"})
    assert response.status_code == 200

    user_in_db = db_session.query(User).filter(User.username == "profile_test").first()
    assert user_in_db.first_name == "New_name"
    assert user_in_db.mail == "updated@test.com"
