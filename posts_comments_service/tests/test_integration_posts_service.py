import pytest
import grpc
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, Post, Comment, PostLike
from app.handlers import PostService
import posts_pb2

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)


class DummyContext:
    def set_code(self, code):
        self.code = code

    def set_details(self, details):
        self.details = details

    def invocation_metadata(self):
        return [("current_user", "test_user")]


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def service(db_session, monkeypatch):
    import app.handlers
    monkeypatch.setattr(app.handlers, 'SessionLocal', TestingSessionLocal)

    class MockProducer:
        def send(self, topic, data): pass

        def flush(self): pass

    monkeypatch.setattr(app.handlers, 'producer', MockProducer())

    return PostService()


def test_create_post_integration(service, db_session):
    request = posts_pb2.CreatePostRequest(
        title="Integration Post",
        description="Test description",
        creator_id="test_user",
        is_private=False,
        tags=["test"]
    )
    context = DummyContext()
    response = service.CreatePost(request, context)

    post_in_db = db_session.query(Post).filter(Post.id == response.post.id).first()
    assert post_in_db is not None
    assert post_in_db.title == "Integration Post"


def test_like_post_integration(service, db_session):
    post = Post(
        id="test_post_id",
        title="Test",
        description="Desc",
        creator_id="test_user"
    )
    db_session.add(post)
    db_session.commit()

    request = posts_pb2.LikeRequest(post_id=str(post.id))
    context = DummyContext()
    response = service.LikePost(request, context)

    like_in_db = db_session.query(PostLike).filter(PostLike.post_id == post.id).first()
    assert like_in_db is not None
    assert like_in_db.user_id == "test_user"


def test_create_comment_integration(service, db_session):
    post = Post(
        id="comment_test_id",
        title="Test",
        description="Desc",
        creator_id="test_user"
    )
    db_session.add(post)
    db_session.commit()

    request = posts_pb2.CreateCommentRequest(
        post_id=str(post.id),
        user_id="commenter",
        content="Test comment"
    )
    context = DummyContext()
    response = service.CreateComment(request, context)

    comment_in_db = db_session.query(Comment).filter(Comment.post_id == post.id).first()
    assert comment_in_db is not None
    assert comment_in_db.content == "Test comment"
