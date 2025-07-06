import pytest
import json
import time
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, Post
from app.handlers import PostService
import posts_pb2

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


class DummyContext:
    def set_code(self, code):
        self.code = code

    def set_details(self, details):
        self.details = details

    def invocation_metadata(self):
        return [("current_user", "test_user")]


def consume_messages(topic, timeout=5):
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=['kafka:9092'],
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        group_id=f'test_group_{int(time.time())}',
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        consumer_timeout_ms=timeout * 1000
    )

    messages = []
    try:
        for message in consumer:
            messages.append(message.value)
            break
    except Exception as e:
        print(f"Consumer error: {e}")
    finally:
        consumer.close()

    return messages


@pytest.fixture
def service(monkeypatch):
    import app.handlers
    monkeypatch.setattr(app.handlers, 'SessionLocal', TestingSessionLocal)

    producer = KafkaProducer(
        bootstrap_servers=['kafka:9092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    monkeypatch.setattr(app.handlers, 'producer', producer)

    return PostService()


@pytest.fixture
def clean_db():
    session = TestingSessionLocal()
    try:
        session.execute("DELETE FROM comments")
        session.execute("DELETE FROM post_likes")
        session.execute("DELETE FROM posts")
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Warning: Could not clean database: {e}")
    finally:
        session.close()


@pytest.fixture
def test_post(clean_db):
    import uuid
    session = TestingSessionLocal()
    try:
        post_id = f"kafka_test_post_{str(uuid.uuid4())[:8]}"
        post = Post(
            id=post_id,
            title="Kafka Test Post",
            description="Test description",
            creator_id="test_user",
            is_private=False,
            tags="test,kafka"
        )
        session.add(post)
        session.commit()
        session.refresh(post)
        return post
    finally:
        session.close()


def test_get_post_sends_view_event(service, test_post):
    request = posts_pb2.GetPostRequest(id=test_post.id)
    context = DummyContext()
    response = service.GetPost(request, context)

    assert response.post.id == test_post.id
    assert response.post.title == "Kafka Test Post"

    time.sleep(1)
    messages = consume_messages('post_views')
    assert len(messages) > 0

    view_event = messages[0]
    assert view_event['post_id'] == test_post.id
    assert view_event['user_id'] == "test_user"
    assert 'viewed_at' in view_event


def test_like_post_sends_like_event(service, test_post):
    request = posts_pb2.LikeRequest(post_id=test_post.id)
    context = DummyContext()
    response = service.LikePost(request, context)
    assert response.message == "Like recorded"

    time.sleep(1)

    messages = consume_messages('post_likes')
    assert len(messages) > 0

    like_event = messages[0]
    assert like_event['post_id'] == test_post.id
    assert like_event['user_id'] == "test_user"
    assert 'liked_at' in like_event


def test_create_comment_sends_comment_event(service, test_post):
    request = posts_pb2.CreateCommentRequest(
        post_id=test_post.id,
        user_id="commenter",
        content="Test Kafka comment"
    )
    context = DummyContext()
    response = service.CreateComment(request, context)

    assert response.comment.content == "Test Kafka comment"
    assert response.comment.post_id == test_post.id

    time.sleep(1)
    messages = consume_messages('post_comments')
    assert len(messages) > 0
    comment_event = messages[0]
    assert comment_event['post_id'] == test_post.id
    assert comment_event['user_id'] == "commenter"
    assert comment_event['content'] == "Test Kafka comment"
    assert 'comment_id' in comment_event
    assert 'commented_at' in comment_event
