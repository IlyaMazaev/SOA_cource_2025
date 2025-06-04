import pytest
import json
from kafka import KafkaProducer, KafkaConsumer
from app.models import Post
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import time

# Настройка тестовой БД
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_kafka_like_event(db_session):
    # Создаем тестовый пост
    post = Post(title="Kafka Test", description="Desc", creator_id="kafka_user")
    db_session.add(post)
    db_session.commit()

    # Отправляем событие в Kafka
    producer = KafkaProducer(
        bootstrap_servers='kafka:9092',
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

    event = {
        "event_type": "like",
        "data": {
            "post_id": str(post.id),
            "user_id": "test_user",
            "liked_at": "2023-01-01T00:00:00"
        }
    }
    producer.send('events', event)
    producer.flush()

    # Даем время на обработку
    time.sleep(5)

    # Проверяем обработку события
    # (В реальном проекте здесь бы проверяли ClickHouse, но для примера проверяем локальную БД)
    # Вместо этого в вашем случае нужно проверять ClickHouse
    likes_count = db_session.query(Like).filter(Like.post_id == post.id).count()
    assert likes_count == 1


def test_kafka_comment_event(db_session):
    # Создаем тестовый пост
    post = Post(title="Kafka Comment", description="Desc", creator_id="kafka_user")
    db_session.add(post)
    db_session.commit()

    # Отправляем событие в Kafka
    producer = KafkaProducer(
        bootstrap_servers='kafka:9092',
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

    event = {
        "event_type": "comment",
        "data": {
            "post_id": str(post.id),
            "user_id": "commenter",
            "content": "Kafka test comment",
            "commented_at": "2023-01-01T00:00:00"
        }
    }
    producer.send('events', event)
    producer.flush()

    # Даем время на обработку
    time.sleep(5)

    # Проверяем обработку события
    comments_count = db_session.query(Comment).filter(Comment.post_id == post.id).count()
    assert comments_count == 1