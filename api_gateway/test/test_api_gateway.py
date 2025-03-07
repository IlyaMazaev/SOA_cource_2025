import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import jwt
import respx
from httpx import Response
from app.auth import create_jwt_token, SECRET_KEY, ALGORITHM
from app.main import app

client = TestClient(app)

@respx.mock
def test_register_proxy_success():
    # Мокаем вызов к user_service /register
    route = respx.post("http://user_service:8001/register").mock(
        return_value=Response(201, json={"message": "User created", "user_id": 1})
    )
    response = client.post("/register", json={
        "username": "proxyuser",
        "password": "password",
        "email": "proxy@example.com"
    })
    assert route.called
    assert response.status_code ==  201
    data = response.json()
    assert data["user_id"] == 1


@respx.mock
def test_login_proxy_success():
    # Мокаем вызов к user_service /login
    user_data = {"user_id": 2, "username": "loginuser", "email": "login@example.com"}
    route = respx.post("http://user_service:8001/login").mock(
        return_value=Response(200, json=user_data)
    )
    response = client.post("/login", json={
        "username": "loginuser",
        "password": "password"
    })
    assert route.called
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    token = data["access_token"]
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "loginuser"
    assert payload["user_id"] == 2
    assert payload["email"] == "login@example.com"


@respx.mock
def test_login_proxy_invalid():
    # Мокаем вызов к user_service /login, возвращающий 401
    route = respx.post("http://user_service:8001/login").mock(
        return_value=Response(401, json={"detail": "Invalid credentials"})
    )
    response = client.post("/login", json={
        "username": "loginuser",
        "password": "wrongpassword"
    })
    assert route.called
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == '{"detail": "Invalid credentials"}'


@respx.mock
def test_get_profile_no_token():
    # Попытка получения профиля без хедера авторизации
    response = client.get("/profile", params={"username": "anyuser"})
    assert response.status_code == 403


@respx.mock
def test_get_profile_invalid_token():
    # Передаем недопустимый токен
    headers = {"Authorization": "Bearer invalid.token.value"}
    response = client.get("/profile", headers=headers, params={"username": "anyuser"})
    assert response.status_code == 401
    data = response.json()
    assert "Invalid token" in data["detail"]


@respx.mock
def test_get_profile_success():
    # Создаем валидный токен
    token = create_jwt_token("profileuser", 3, "profile@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    # Мокаем вызов к user_service /profile
    profile_data = {
        "username": "profileuser",
        "email": "profile@example.com",
        "first_name": "Alice",
        "last_name": "Smith",
        "birth_date": None,
        "mail": None,
        "phone": None,
        "created_at": "2025-01-01T00:00:00",
        "updated_at": "2025-01-01T00:00:00"
    }
    route = respx.get("http://user_service:8001/profile").mock(
        return_value=Response(200, json=profile_data)
    )
    response = client.get("/profile", headers=headers)
    assert route.called
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "profileuser"
    assert data["email"] == "profile@example.com"


@respx.mock
def test_put_profile_success():
    # Создаем валидный токен
    token = create_jwt_token("updateuser", 4, "update@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    # Мокаем вызов к user_service PUT /profile
    route = respx.put("http://user_service:8001/profile").mock(
        return_value=Response(200, json={"message": "Profile updated"})
    )
    response = client.put("/profile", headers=headers, params={"username": "updateuser"}, json={
        "first_name": "Bob",
        "last_name": "Marley",
        "mail": "bob.marley@example.com",
        "phone": "555-1234"
    })
    assert route.called
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Profile updated"


@respx.mock
def test_get_profile_expired_token():
    # Создаем токен с истекшим сроком действия
    expired_time = datetime.utcnow() - timedelta(minutes=5)
    payload = {
        "sub": "expireduser",
        "user_id": 5,
        "email": "expired@example.com",
        "exp": expired_time
    }
    expired_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.get("/profile", headers=headers, params={"username": "expireduser"})
    assert response.status_code == 401
    data = response.json()
    assert "expired" in data["detail"].lower()
