import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import jwt
import respx
import grpc
from httpx import Response
from app.auth import create_jwt_token, SECRET_KEY, ALGORITHM
from app.main import app
import posts_pb2
from app import handlers
client = TestClient(app)

@respx.mock
def test_register_proxy_success():
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
    response = client.get("/profile", params={"username": "anyuser"})
    assert response.status_code == 403


@respx.mock
def test_get_profile_invalid_token():
    headers = {"Authorization": "Bearer invalid.token.value"}
    response = client.get("/profile", headers=headers, params={"username": "anyuser"})
    assert response.status_code == 401
    data = response.json()
    assert "Invalid token" in data["detail"]


@respx.mock
def test_get_profile_success():
    token = create_jwt_token("profileuser", 3, "profile@example.com")
    headers = {"Authorization": f"Bearer {token}"}
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
    token = create_jwt_token("updateuser", 4, "update@example.com")
    headers = {"Authorization": f"Bearer {token}"}
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

class DummyPostServiceStub:
    def CreatePost(self, request, metadata=None):
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

    def GetPost(self, request, metadata=None):
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

    def UpdatePost(self, request, metadata=None):
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

    def DeletePost(self, request, metadata=None):
        return posts_pb2.DeletePostResponse(message="Post deleted")

    def ListPosts(self, request, metadata=None):
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

@pytest.fixture(autouse=True)
def override_get_posts_stub(monkeypatch):
    monkeypatch.setattr(handlers, "get_posts_stub", lambda: DummyPostServiceStub())

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
    class ForbiddenUpdateStub:
        def UpdatePost(self, request):
            raise Exception("Access denied: not the owner")

        def CreatePost(self, request, metadata=None):
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

        def GetPost(self, request, metadata=None):
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

        def DeletePost(self, request, metadata=None):
            return posts_pb2.DeletePostResponse(message="Post deleted")

        def ListPosts(self, request, metadata=None):
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
        def DeletePost(self, request, metadata=None):
            raise Exception("Access denied: not the owner")

        def CreatePost(self, request, metadata=None):
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

        def GetPost(self, request, metadata=None):
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

        def UpdatePost(self, request, metadata=None):
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

        def ListPosts(self, request, metadata=None):
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

def test_view_post_success(monkeypatch):
    class Stub:
        def ViewPost(self, request, metadata=None):
            return posts_pb2.ViewResponse(message='viewed')
    monkeypatch.setattr(handlers, 'get_posts_stub', lambda: Stub())
    response = client.post('/posts/123/view', headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == {'message': 'viewed'}


def test_like_post_success(monkeypatch):
    class Stub:
        def LikePost(self, request, metadata=None):
            return posts_pb2.LikeResponse(message='liked')
    monkeypatch.setattr(handlers, 'get_posts_stub', lambda: Stub())
    response = client.post('/posts/123/like', headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == {'message': 'liked'}


def test_create_comment_success(monkeypatch):
    class Stub:
        def CreateComment(self, request, metadata=None):
            return posts_pb2.CreateCommentResponse(
                comment=posts_pb2.Comment(
                    id='c1', post_id=request.post_id,
                    user_id=request.user_id,
                    content=request.content,
                    created_at='t'
                )
            )
    monkeypatch.setattr(handlers, 'get_posts_stub', lambda: Stub())
    payload = {'content': 'hi'}
    response = client.post('/posts/123/comments', json=payload, headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data['id'] == 'c1'
    assert data['post_id'] == '123'
    assert data['content'] == 'hi'


def test_list_comments_success(monkeypatch):
    class Stub:
        def ListComments(self, request, metadata=None):
            return posts_pb2.ListCommentsResponse(comments=[
                posts_pb2.Comment(id='c1', post_id=request.post_id, user_id='u1', content='a', created_at='t1'),
                posts_pb2.Comment(id='c2', post_id=request.post_id, user_id='u2', content='b', created_at='t2')
            ])
    monkeypatch.setattr(handlers, 'get_posts_stub', lambda: Stub())
    response = client.get('/posts/123/comments?page=0&page_size=2', headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list) and len(data) == 2
    assert data[0]['id'] == 'c1'


def test_like_post_error(monkeypatch):
    class Stub:
        def LikePost(self, request, metadata=None):
            raise grpc.RpcError('fail')
    monkeypatch.setattr(handlers, 'get_posts_stub', lambda: Stub())
    response = client.post('/posts/123/like', headers=HEADERS)
    assert response.status_code == 500
    assert 'gRPC error' in response.json()['detail']

