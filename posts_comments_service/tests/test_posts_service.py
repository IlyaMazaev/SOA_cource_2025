import pytest
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, Post
from app.handlers import PostService, post_to_proto
import posts_pb2

# Создаем in‑memory SQLite базу для тестирования
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

import app.handlers as server_module

server_module.SessionLocal = TestingSessionLocal


class DummyContext:
    def __init__(self):
        self.code = None
        self.details = None
        self.metadata = ()

    def set_code(self, code):
        self.code = code

    def set_details(self, details):
        self.details = details

    def invocation_metadata(self):
        return self.metadata


@pytest.fixture
def context():
    return DummyContext()


@pytest.fixture
def service():
    return PostService()


def test_create_post(service, context):
    request = posts_pb2.CreatePostRequest(
        title="Test Post",
        description="Description",
        creator_id="testuser",
        is_private=False,
        tags=["tag1", "tag2"]
    )
    response = service.CreatePost(request, context)
    assert response.post.title == "Test Post"
    assert response.post.creator_id == "testuser"
    assert response.post.tags == ["tag1", "tag2"]


def test_get_post(service, context):
    create_request = posts_pb2.CreatePostRequest(
        title="Test Post",
        description="Description",
        creator_id="testuser",
        is_private=False,
        tags=["tag1"]
    )
    create_response = service.CreatePost(create_request, context)
    post_id = create_response.post.id

    get_request = posts_pb2.GetPostRequest(id=post_id)
    get_response = service.GetPost(get_request, context)
    assert get_response.post.id == post_id
    assert get_response.post.title == "Test Post"


def test_update_post(service, context):
    create_request = posts_pb2.CreatePostRequest(
        title="Original Title",
        description="Original Desc",
        creator_id="testuser",
        is_private=False,
        tags=["tag1"]
    )
    create_response = service.CreatePost(create_request, context)
    post_id = create_response.post.id

    # Обновляем пост
    update_request = posts_pb2.UpdatePostRequest(
        id=post_id,
        title="Updated Title",
        description="Updated Desc",
        is_private=True,
        tags=["tag2"]
    )
    context.metadata = (("current_user", "testuser"),)
    update_response = service.UpdatePost(update_request, context)
    assert update_response.post.title == "Updated Title"
    assert update_response.post.is_private is True
    assert update_response.post.tags == ["tag2"]


def test_delete_post(service, context):
    create_request = posts_pb2.CreatePostRequest(
        title="Post to Delete",
        description="Desc",
        creator_id="testuser",
        is_private=False,
        tags=[]
    )
    create_response = service.CreatePost(create_request, context)
    post_id = create_response.post.id
    context.metadata = (("current_user", "testuser"),)

    delete_request = posts_pb2.DeletePostRequest(id=post_id)
    delete_response = service.DeletePost(delete_request, context)
    assert delete_response.message == "Post deleted"

    get_request = posts_pb2.GetPostRequest(id=post_id)
    get_response = service.GetPost(get_request, context)
    assert context.code is not None


def test_update_stranger_post(service, context):
    create_request = posts_pb2.CreatePostRequest(
        title="Original Title",
        description="Original Desc",
        creator_id="testuser",
        is_private=False,
        tags=["tag1"]
    )
    create_response = service.CreatePost(create_request, context)
    post_id = create_response.post.id

    # Обновляем пост
    update_request = posts_pb2.UpdatePostRequest(
        id=post_id,
        title="Updated Title",
        description="Updated Desc",
        is_private=True,
        tags=["tag2"]
    )
    context.metadata = (("current_user", "wronguser"),)
    update_response = service.UpdatePost(update_request, context)
    assert context.code == "PERMISSION_DENIED"


def test_delete_stranger_post(service, context):
    create_request = posts_pb2.CreatePostRequest(
        title="Post to Delete",
        description="Desc",
        creator_id="testuser",
        is_private=False,
        tags=[]
    )
    create_response = service.CreatePost(create_request, context)
    post_id = create_response.post.id
    context.metadata = (("current_user", "wronguser"),)

    delete_request = posts_pb2.DeletePostRequest(id=post_id)
    delete_response = service.DeletePost(delete_request, context)
    assert context.code == "PERMISSION_DENIED"


def clear_db():
    session = TestingSessionLocal()
    session.query(Post).delete()
    session.commit()
    session.close()


def test_list_posts(service, context):
    clear_db()
    create_request = posts_pb2.CreatePostRequest(
        title="List Post",
        description="Desc",
        creator_id="testuser",
        is_private=False,
        tags=["tag1"]
    )
    service.CreatePost(create_request, context)
    list_request = posts_pb2.ListPostsRequest(page=0, page_size=10)
    list_response = service.ListPosts(list_request, context)
    assert len(list_response.posts) == 1


def test_create_post_private(service, context):
    request = posts_pb2.CreatePostRequest(
        title="Private Post",
        description="Secret",
        creator_id="testuser",
        is_private=True,
        tags=["secret"]
    )
    response = service.CreatePost(request, context)
    assert response.post.is_private is True
    context.metadata = (("current_user", "testuser"),)
    get_request = posts_pb2.GetPostRequest(id=response.post.id)
    get_response = service.GetPost(get_request, context)
    assert get_response.post.is_private is True


def test_pagination_detailed(service, context):
    clear_db()
    num_posts = 5
    for i in range(num_posts):
        request = posts_pb2.CreatePostRequest(
            title=f"Post {i}",
            description=f"Desc {i}",
            creator_id="testuser",
            is_private=False,
            tags=[f"tag{i}"]
        )
        service.CreatePost(request, context)

    list_request = posts_pb2.ListPostsRequest(page=0, page_size=6)
    list_response = service.ListPosts(list_request, context)
    assert len(list_response.posts) == 5

    list_request = posts_pb2.ListPostsRequest(page=1, page_size=5)
    list_response = service.ListPosts(list_request, context)
    assert len(list_response.posts) == 0

    list_request = posts_pb2.ListPostsRequest(page=0, page_size=2)
    list_response = service.ListPosts(list_request, context)
    assert len(list_response.posts) == 2

    list_request = posts_pb2.ListPostsRequest(page=1, page_size=2)
    list_response = service.ListPosts(list_request, context)
    assert len(list_response.posts) == 2

    list_request = posts_pb2.ListPostsRequest(page=2, page_size=2)
    list_response = service.ListPosts(list_request, context)
    assert len(list_response.posts) == 1

    list_request = posts_pb2.ListPostsRequest(page=3, page_size=2)
    list_response = service.ListPosts(list_request, context)
    assert len(list_response.posts) == 0


def test_workflow(service, context):
    clear_db()
    create_request = posts_pb2.CreatePostRequest(
        title="Workflow Post",
        description="Initial",
        creator_id="testuser",
        is_private=False,
        tags=["start"]
    )
    create_response = service.CreatePost(create_request, context)
    post_id = create_response.post.id
    context.metadata = (("current_user", "testuser"),)
    get_response = service.GetPost(posts_pb2.GetPostRequest(id=post_id), context)
    assert get_response.post.title == "Workflow Post"
    update_request = posts_pb2.UpdatePostRequest(
        id=post_id,
        title="Workflow Post Updated",
        description="Updated",
        is_private=True,
        tags=["updated"]
    )
    update_response = service.UpdatePost(update_request, context)
    assert update_response.post.title == "Workflow Post Updated"
    assert update_response.post.is_private is True
    context.metadata = (("current_user", "testuser"),)
    get_response = service.GetPost(posts_pb2.GetPostRequest(id=post_id), context)
    assert get_response.post.description == "Updated"

    delete_response = service.DeletePost(posts_pb2.DeletePostRequest(id=post_id), context)
    assert delete_response.message == "Post deleted"
    service.GetPost(posts_pb2.GetPostRequest(id=post_id), context)
    assert context.code is not None


def test_get_nonexistent_post(service, context):
    clear_db()
    fake_id = "non-existent-id"
    service.GetPost(posts_pb2.GetPostRequest(id=fake_id), context)
    assert context.code is not None


def test_update_nonexistent_post(service, context):
    clear_db()
    fake_id = "non-existent-id"
    update_request = posts_pb2.UpdatePostRequest(
        id=fake_id,
        title="Does not exist",
        description="",
        is_private=False,
        tags=[]
    )
    service.UpdatePost(update_request, context)
    assert context.code is not None


def test_delete_nonexistent_post(service, context):
    clear_db()
    fake_id = "non-existent-id"
    service.DeletePost(posts_pb2.DeletePostRequest(id=fake_id), context)
    assert context.code is not None


def test_list_posts_empty(service, context):
    clear_db()
    list_request = posts_pb2.ListPostsRequest(page=0, page_size=10)
    list_response = service.ListPosts(list_request, context)
    assert len(list_response.posts) == 0


def test_private_post_access_forbidden(service, context):
    create_request = posts_pb2.CreatePostRequest(
        title="Private Post",
        description="Secret content",
        creator_id="user1",
        is_private=True,
        tags=["confidential"]
    )
    create_response = service.CreatePost(create_request, context)
    post_id = create_response.post.id

    context.metadata = (("current_user", "user2"),)

    get_request = posts_pb2.GetPostRequest(id=post_id)
    service.GetPost(get_request, context)

    assert context.code == "PERMISSION_DENIED"
