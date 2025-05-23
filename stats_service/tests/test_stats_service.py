import pytest
import stats_pb2
from app.handlers import StatsService
import grpc
import datetime


class DummyContext:
    def __init__(self):
        self.code = None
        self.details = None

    def set_code(self, code):
        self.code = code

    def set_details(self, details):
        self.details = details


@pytest.fixture
def context():
    return DummyContext()


@pytest.fixture
def service(monkeypatch):
    mock_client = type("MockClient", (), {})()

    def mock_query(query):
        class Result:
            @property
            def result_rows(self):
                if "GROUP BY" in query:
                    if "post_id" in query and "GROUP BY date" in query:
                        return [
                            (datetime.date(2025, 1, 1), 1),
                            (datetime.date(2025, 1, 2), 2),
                        ]
                    elif "post_id" in query:
                        return [("post1", 5), ("post2", 3)]
                    elif "user_id" in query:
                        return [("user1", 10), ("user2", 8)]
                return [(7,)]

        return Result()

    mock_client.query = mock_query
    monkeypatch.setattr("app.handlers.client", mock_client)
    return StatsService()


def test_get_post_stats(service, context):
    request = stats_pb2.PostStatsRequest(post_id="post1")
    response = service.GetPostStats(request, context)
    assert response.likes == 7
    assert response.views == 7
    assert response.comments == 7
    assert context.code is None


def test_get_post_views_history(service, context):
    request = stats_pb2.PostStatsRequest(post_id="post1")
    response = service.GetPostViewsHistory(request, context)
    assert len(response.history) == 2
    assert response.history[0].date == "2025-01-01"
    assert response.history[0].stat == 1


def test_get_post_likes_history(service, context):
    request = stats_pb2.PostStatsRequest(post_id="post1")
    response = service.GetPostLikesHistory(request, context)
    assert len(response.history) == 2
    assert response.history[1].date == "2025-01-02"
    assert response.history[1].stat == 2


def test_get_post_comments_history(service, context):
    request = stats_pb2.PostStatsRequest(post_id="post1")
    response = service.GetPostCommentsHistory(request, context)
    assert len(response.history) == 2


def test_get_top_ten_posts(service, context):
    request = stats_pb2.TopTenPostsRequest(param=stats_pb2.LIKES)
    response = service.GetTopTenPosts(request, context)
    assert response.post_ids == ["post1", "post2"]


def test_get_top_ten_users(service, context):
    request = stats_pb2.TopTenUsersRequest(param=stats_pb2.VIEWS)
    response = service.GetTopTenUsers(request, context)
    assert response.user_ids == ["user1", "user2"]
