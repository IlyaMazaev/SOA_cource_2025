import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import jwt
import respx
from httpx import Response
from app.auth import create_jwt_token, SECRET_KEY, ALGORITHM
from app.main import app
import posts_pb2
from app import handlers
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

# Создадим фиктивный stub, который возвращает заранее определённые ответы
class DummyPostServiceStub:
    def CreatePost(self, request):
        dummy_post = posts_pb2.Post(
            id="dummy-id",
            title=request.title,
            description=request.description,
            creator_id=request.creator_id,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
            is_private=request.is_private,
            tags=request.tags,
        )
        return posts_pb2.CreatePostResponse(post=dummy_post)

    def GetPost(self, request):
        # Если запрошен несуществующий id, можно имитировать ошибку (здесь упрощённо – всегда возвращаем dummy)
        dummy_post = posts_pb2.Post(
            id=request.id,
            title="Test Title",
            description="Test Description",
            creator_id="user123",
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
            is_private=False,
            tags=["tag1", "tag2"],
        )
        return posts_pb2.GetPostResponse(post=dummy_post)

    def UpdatePost(self, request):
        dummy_post = posts_pb2.Post(
            id=request.id,
            title=request.title,
            description=request.description,
            creator_id="user123",
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-02T00:00:00",
            is_private=request.is_private,
            tags=request.tags,
        )
        return posts_pb2.UpdatePostResponse(post=dummy_post)

    def DeletePost(self, request):
        return posts_pb2.DeletePostResponse(message="Post deleted")

    def ListPosts(self, request):
        dummy_post = posts_pb2.Post(
            id="dummy-id",
            title="Test Title",
            description="Test Description",
            creator_id="user123",
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
            is_private=False,
            tags=["tag1", "tag2"],
        )
        return posts_pb2.ListPostsResponse(posts=[dummy_post])

# Патчим функцию get_posts_stub, чтобы она возвращала наш DummyPostServiceStub
@pytest.fixture(autouse=True)
def override_get_posts_stub(monkeypatch):
    monkeypatch.setattr(handlers, "get_posts_stub", lambda: DummyPostServiceStub())

# Создаем валидный токен для авторизации (используйте вашу функцию создания токена)
TOKEN = create_jwt_token("user123", 123, "user@example.com")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

def test_create_post():
    payload = {
        "title": "New Post",
        "description": "New post description",
        "is_private": False,
        "tags": ["tag1", "tag2"]
    }
    response = client.post("/posts", json=payload, headers=HEADERS)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "dummy-id"
    assert data["title"] == payload["title"]

def test_get_post():
    response = client.get("/posts/dummy-id", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "dummy-id"
    assert data["title"] == "Test Title"

def test_update_post():
    payload = {
        "title": "Updated Title",
        "description": "Updated Description",
        "is_private": True,
        "tags": ["tag3"]
    }
    response = client.put("/posts/dummy-id", json=payload, headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["is_private"] == payload["is_private"]

def test_delete_post():
    response = client.delete("/posts/dummy-id", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["detail"] == "Post deleted"

def test_list_posts():
    response = client.get("/posts?page=0&page_size=10", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["id"] == "dummy-id"


def test_update_post_forbidden_api():
    from app import handlers
    # Создаем stub, в котором UpdatePost симулирует отказ для не-владельца
    class ForbiddenUpdateStub:
        def UpdatePost(self, request):
            raise Exception("Access denied: not the owner")

        def CreatePost(self, request):
            dummy_post = posts_pb2.Post(
                id="forbid-id",
                title=request.title,
                description=request.description,
                creator_id=request.creator_id,
                created_at="2025-01-01T00:00:00",
                updated_at="2025-01-01T00:00:00",
                is_private=request.is_private,
                tags=request.tags,
            )
            return posts_pb2.CreatePostResponse(post=dummy_post)

        def GetPost(self, request):
            dummy_post = posts_pb2.Post(
                id=request.id,
                title="Test Title",
                description="Test Description",
                creator_id="user1",
                created_at="2025-01-01T00:00:00",
                updated_at="2025-01-01T00:00:00",
                is_private=True,
                tags=["tag1", "tag2"],
            )
            return posts_pb2.GetPostResponse(post=dummy_post)

        def DeletePost(self, request):
            return posts_pb2.DeletePostResponse(message="Post deleted")

        def ListPosts(self, request):
            dummy_post = posts_pb2.Post(
                id="dummy-id",
                title="Test Title",
                description="Test Description",
                creator_id="user1",
                created_at="2025-01-01T00:00:00",
                updated_at="2025-01-01T00:00:00",
                is_private=False,
                tags=["tag1", "tag2"],
            )
            return posts_pb2.ListPostsResponse(posts=[dummy_post])

    original_stub = handlers.get_posts_stub
    handlers.get_posts_stub = lambda: ForbiddenUpdateStub()

    token_user2 = create_jwt_token("user2", 222, "user2@example.com")
    headers = {"Authorization": f"Bearer {token_user2}"}
    response = client.put("/posts/forbid-id", json={
        "title": "Updated Title",
        "description": "Updated Desc",
        "is_private": True,
        "tags": ["newtag"]
    }, headers=headers)
    assert response.status_code == 403
    handlers.get_posts_stub = original_stub


def test_delete_post_forbidden_api():
    from app import handlers
    class ForbiddenDeleteStub:
        def DeletePost(self, request):
            raise Exception("Access denied: not the owner")

        def CreatePost(self, request):
            dummy_post = posts_pb2.Post(
                id="forbid-id",
                title=request.title,
                description=request.description,
                creator_id=request.creator_id,
                created_at="2025-01-01T00:00:00",
                updated_at="2025-01-01T00:00:00",
                is_private=request.is_private,
                tags=request.tags,
            )
            return posts_pb2.CreatePostResponse(post=dummy_post)

        def GetPost(self, request):
            dummy_post = posts_pb2.Post(
                id=request.id,
                title="Test Title",
                description="Test Description",
                creator_id="user1",
                created_at="2025-01-01T00:00:00",
                updated_at="2025-01-01T00:00:00",
                is_private=True,
                tags=["tag1", "tag2"],
            )
            return posts_pb2.GetPostResponse(post=dummy_post)

        def UpdatePost(self, request):
            dummy_post = posts_pb2.Post(
                id=request.id,
                title=request.title,
                description=request.description,
                creator_id="user1",
                created_at="2025-01-01T00:00:00",
                updated_at="2025-01-01T00:00:00",
                is_private=request.is_private,
                tags=request.tags,
            )
            return posts_pb2.UpdatePostResponse(post=dummy_post)

        def ListPosts(self, request):
            dummy_post = posts_pb2.Post(
                id="dummy-id",
                title="Test Title",
                description="Test Description",
                creator_id="user1",
                created_at="2025-01-01T00:00:00",
                updated_at="2025-01-01T00:00:00",
                is_private=False,
                tags=["tag1", "tag2"],
            )
            return posts_pb2.ListPostsResponse(posts=[dummy_post])

    original_stub = handlers.get_posts_stub
    handlers.get_posts_stub = lambda: ForbiddenDeleteStub()

    token_user2 = create_jwt_token("user2", 222, "user2@example.com")
    headers = {"Authorization": f"Bearer {token_user2}"}
    response = client.delete("/posts/forbid-id", headers=headers)
    assert response.status_code == 403
    handlers.get_posts_stub = original_stub