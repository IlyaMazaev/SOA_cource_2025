import pytest
import requests
import time

BASE_URL = "http://api_gateway:8000"  # Для запуска внутри Docker


@pytest.fixture
def auth_headers():
    # Регистрация пользователя
    user_data = {
        "username": "e2e_test_user",
        "password": "e2e_password",
        "email": "e2e@test.com"
    }
    requests.post(f"{BASE_URL}/register", json=user_data)

    # Логин и получение токена
    login_resp = requests.post(f"{BASE_URL}/login", json={
        "username": "e2e_test_user",
        "password": "e2e_password"
    })
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_full_post_workflow(auth_headers):
    # Создание поста
    post_data = {
        "title": "E2E Test Post",
        "description": "End-to-end test description",
        "is_private": False,
        "tags": ["e2e", "test"]
    }
    create_resp = requests.post(f"{BASE_URL}/posts", json=post_data, headers=auth_headers)
    assert create_resp.status_code == 201
    post_id = create_resp.json()["id"]

    # Получение поста
    get_resp = requests.get(f"{BASE_URL}/posts/{post_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "E2E Test Post"

    # Добавление лайка
    like_resp = requests.post(f"{BASE_URL}/posts/{post_id}/like", headers=auth_headers)
    assert like_resp.status_code == 200

    # Добавление комментария
    comment_resp = requests.post(
        f"{BASE_URL}/posts/{post_id}/comments",
        json={"content": "E2E test comment"},
        headers=auth_headers
    )
    assert comment_resp.status_code == 200

    # Ждем обработки событий
    time.sleep(10)

    # Проверка статистики
    stats_resp = requests.get(f"{BASE_URL}/posts/{post_id}/stats", headers=auth_headers)
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["likes"] >= 1
    assert stats["comments"] >= 1


def test_user_profile_workflow(auth_headers):
    # Получение профиля
    profile_resp = requests.get(f"{BASE_URL}/profile", headers=auth_headers)
    assert profile_resp.status_code == 200
    profile = profile_resp.json()

    # Обновление профиля
    update_data = {
        "first_name": "E2E",
        "last_name": "Test",
        "mail": "updated@e2e.com"
    }
    update_resp = requests.put(f"{BASE_URL}/profile", json=update_data, headers=auth_headers)
    assert update_resp.status_code == 200

    # Проверка обновлений
    updated_profile = requests.get(f"{BASE_URL}/profile", headers=auth_headers).json()
    assert updated_profile["first_name"] == "E2E"
    assert updated_profile["mail"] == "updated@e2e.com"


def test_top_posts_workflow(auth_headers):
    # Создаем несколько постов с активностью
    for i in range(3):
        post_resp = requests.post(f"{BASE_URL}/posts", json={
            "title": f"Top Post {i}",
            "description": f"Description {i}",
            "is_private": False,
            "tags": ["top"]
        }, headers=auth_headers)
        post_id = post_resp.json()["id"]

        # Добавляем лайки
        for _ in range(i + 1):
            requests.post(f"{BASE_URL}/posts/{post_id}/like", headers=auth_headers)

    # Ждем обработки
    time.sleep(15)

    # Получаем топ постов
    top_resp = requests.get(f"{BASE_URL}/top/posts?sort_by=likes", headers=auth_headers)
    assert top_resp.status_code == 200
    top_posts = top_resp.json()["post_ids"]

    # Проверяем что посты отсортированы по количеству лайков
    assert len(top_posts) >= 3