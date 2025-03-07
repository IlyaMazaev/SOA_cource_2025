import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import  Base, get_db
from app.main import app

# Создадим in-memory SQLite базу для тестирования
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

client = TestClient(app)


def test_register():
    # Тест регистрации пользователя
    response = client.post("/register", json={
        "username": "user",
        "password": "password",
        "email": "email@example.com"
    })
    assert response.status_code == 201
    data = response.json()
    assert "user_id" in data
    
def test_register():
    # Регистрация пользователя
    response = client.post("/register", json={
        "username": "reguser",
        "password": "password",
        "email": "reg@example.com"
    })
    assert response.status_code == 201
    data = response.json()
    assert "user_id" in data
    
    # Повторная регистрация пользователя
    response = client.post("/register", json={
        "username": "reguser",
        "password": "password",
        "email": "reg@example.com"
    })
    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Username already exists"
    

def test_register_with_short_password():
    # Регистрация с паролем короче требуемых 5 символов
    response = client.post("/register", json={
        "username": "shortpass",
        "password": "123",  # недостаточная длина
        "email": "shortpass@example.com"
    })
    assert response.status_code == 422
    
def test_register_invalid_email():
    # Тест регистрации пользователя с почтой неверного формата
    response = client.post("/register", json={
        "username": "email_reguser",
        "password": "password",
        "email": "aboba"
    })
    assert response.status_code == 422, f"Login failed: {response.text}"
    data = response.json()
    data["detail"] == '{"detail":[{"loc":["body","email"],"msg":"value is not a valid email address","type":"value_error.email"}]}'
    

def test_register_missing_fields():
    # Регистрация без поля password
    response = client.post("/register", json={
        "username": "user_missing_pass",
        "email": "missing_pass@example.com"
    })
    assert response.status_code == 422

    # Регистрация без поля email
    response = client.post("/register", json={
        "username": "user_missing_email",
        "password": "validpassword"
    })
    assert response.status_code == 422

    # Регистрация без поля username
    response = client.post("/register", json={
        "password": "validpassword",
        "email": "missing_user@example.com"
    })
    assert response.status_code == 422

    
def test_register_and_login():
    # Тест регистрации нового пользователя
    response = client.post("/register", json={
        "username": "testuser",
        "password": "secret123",
        "email": "test@example.com"
    })
    assert response.status_code == 201
    data = response.json()
    assert "user_id" in data

    # Тест логина зарегистрированного пользователя
    response = client.post("/login", json={
        "username": "testuser",
        "password": "secret123"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert "user_id" in data
    
def test_login_nonexistent_user():
    # Попытка логина для несуществующего пользователя
    response = client.post("/login", json={
        "username": "nonexistent",
        "password": "any_password"
    })
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Invalid credentials"

def test_login_empty_payload():
    # Попытка логина с пустым JSON телом
    response = client.post("/login", json={})
    assert response.status_code == 422
    
def test_login_missing_fields():
    # Логин с отсутствующим полем password
    response = client.post("/login", json={
        "username": "user_without_password"
    })
    assert response.status_code == 422

    # Логин с отсутствующим полем username
    response = client.post("/login", json={
        "password": "some_password"
    })
    assert response.status_code == 422


def test_register_and_login_under_wrong_password():
    # Тест регистрации нового пользователя
    response = client.post("/register", json={
        "username": "wronguser",
        "password": "correct",
        "email": "wrong@example.com"
    })
    assert response.status_code == 201
    data = response.json()
    assert "user_id" in data

    # Тест логина под неверным паролем
    response = client.post("/login", json={
        "username": "wronguser",
        "password": "wrong"
    })
    assert response.status_code == 401
    data = response.json()
    
    assert data["detail"] == "Invalid credentials"

def test_get_and_update_profile_complex():
    # Регистрируем пользователя для теста профиля
    response = client.post("/register", json={
        "username": "profileuser",
        "password": "profilepass",
        "email": "profile@example.com"
    })
    # Если пользователь уже существует, можно продолжать
    if response.status_code not in (201, 400):
        pytest.fail("Unexpected response during registration")

    # Проверка логина
    response = client.post("/login", json={
        "username": "profileuser",
        "password": "profilepass"
    })
    assert response.status_code == 200

    # Получение профиля (изначально поля должны быть пустыми)
    response = client.get("/profile", params={"username": "profileuser"})
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "profileuser"
    # Допустим, что поля first_name и прочие изначально None
    assert data["first_name"] is None

    # Обновление профиля
    response = client.put("/profile", params={"username": "profileuser"}, json={
        "first_name": "John",
        "last_name": "Doe",
        "mail": "john.doe@example.com",
        "phone": "1234567890"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Profile updated"

    # Получение профиля после обновления
    response = client.get("/profile", params={"username": "profileuser"})
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "John"
    assert data["last_name"] == "Doe"
    assert data["mail"] == "john.doe@example.com"
    assert data["phone"] == "1234567890"
    
def test_change_name ():
    response = client.get("/profile", params={"username": "profileuser"})
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "John"
    
    response = client.put("/profile", params={"username": "profileuser"}, json={
        "first_name": "New Name"})
    
    response = client.get("/profile", params={"username": "profileuser"})
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "New Name"
    
    
def test_change_password():
    # Попытка изменения пароля
    response = client.put("/profile", params={"username": "profileuser"}, json={
        "password": "newpassword123"
    })
    # Запрос должен выполниться, так как поле пароля игнорируется
    assert response.status_code == 200
    
    # Проверяем, что логин с оригинальным паролем проходит успешно
    response = client.post("/login", json={
        "username": "profileuser",
        "password": "profilepass"
    })
    assert response.status_code == 200

    # Попытка логина с новым паролем должна завершиться ошибкой
    response = client.post("/login", json={
        "username": "profileuser",
        "password": "newpassword123"
    })
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Invalid credentials"
    
def test_change_login():

    response = client.put("/profile", params={"username": "profileuser"}, json={
        "username": "updated_username",
        "first_name": "Updated_name_with_username"
    })
    # Ожидаем, что запрос пройдет успешно, но поле username будет проигнорировано
    assert response.status_code == 200

    # Проверяем, что логин остался прежним
    response = client.get("/profile", params={"username": "profileuser"})
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "profileuser"
    assert data["first_name"] == "Updated_name_with_username"
    
    # А обновленного логина, в свою очередь, нет в базе.
    response = client.get("/profile", params={"username": "updated_username"})
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "User not found"
    

def test_get_profile_nonexistent_user():
    # Попытка получить профиль для несуществующего пользователя
    response = client.get("/profile", params={"username": "nonexistent_profile"})
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "User not found"


def test_update_profile_nonexistent_user():
    # Попытка обновления профиля для несуществующего пользователя
    response = client.put("/profile", params={"username": "nonexistent_profile"}, json={
        "first_name": "Jane"
    })
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "User not found"
    