import pytest
import grpc
import time
import json
import datetime
from kafka import KafkaProducer

from stats_pb2 import PostStatsRequest, TopTenPostsRequest, SortParam
from app.handlers import StatsService


@pytest.fixture(scope="module")
def kafka_producer():
    producer = KafkaProducer(
        bootstrap_servers=['kafka:9092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    yield producer
    producer.flush()


@pytest.fixture
def stats_service():
    return StatsService()


def test_get_top_posts_integration(stats_service, kafka_producer):
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    kafka_producer.send('post_likes', {
        'post_id': 'post1',
        'user_id': 'user1',
        'liked_at': now
    })
    kafka_producer.send('post_likes', {
        'post_id': 'post1',
        'user_id': 'user2',
        'liked_at': now
    })
    kafka_producer.send('post_likes', {
        'post_id': 'post2',
        'user_id': 'user3',
        'liked_at': now
    })

    kafka_producer.flush()
    time.sleep(5)

    request = TopTenPostsRequest(param=SortParam.LIKES)
    response = stats_service.GetTopTenPosts(request, None)

    assert "post1" in response.post_ids
    assert "post2" in response.post_ids
    assert response.post_ids == ["post1", "post2"]


def test_get_post_stats_integration(stats_service, kafka_producer):
    post_id = "test_post_123"
    user_id = "user1"
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    kafka_producer.send('post_views', {
        'post_id': post_id,
        'user_id': user_id,
        'viewed_at': now
    })

    kafka_producer.send('post_likes', {
        'post_id': post_id,
        'user_id': user_id,
        'liked_at': now
    })

    COMMENTS_NUMBER = 3
    for _ in range(COMMENTS_NUMBER):
        kafka_producer.send('post_comments', {
            'post_id': post_id,
            'comment_id': "c123",
            'user_id': user_id,
            'content': 'Test comment',
            'commented_at': now
        })

    kafka_producer.flush()

    time.sleep(5)

    request = PostStatsRequest(post_id=post_id)
    response = stats_service.GetPostStats(request, None)

    assert response.views == 1
    assert response.likes == 1
    assert response.comments == COMMENTS_NUMBER


def test_get_views_history_integration(stats_service, kafka_producer):
    post_id = "test_post_hist"
    kafka_producer.send('post_views', {
        'post_id': post_id,
        'user_id': 'user1',
        'viewed_at': '2025-01-01 00:00:00'
    })
    kafka_producer.send('post_views', {
        'post_id': post_id,
        'user_id': 'user2',
        'viewed_at': '2025-01-01 12:00:00'
    })
    kafka_producer.send('post_views', {
        'post_id': post_id,
        'user_id': 'user3',
        'viewed_at': '2025-01-02 00:00:00'
    })

    kafka_producer.flush()
    time.sleep(5)

    request = PostStatsRequest(post_id=post_id)
    response = stats_service.GetPostViewsHistory(request, None)

    dates = [day_stats.date for day_stats in response.history]
    assert "2025-01-01" in dates
    assert "2025-01-02" in dates
