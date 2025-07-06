import pytest
import requests
import time
from typing import Dict, Optional
from faker import Faker

fake = Faker()

API_BASE_URL = "http://api_gateway:8000"

class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.access_token: Optional[str] = None

    def set_auth_token(self, token: str):
        """Установить токен авторизации"""
        self.access_token = token
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def clear_auth(self):
        """Очистить авторизацию"""
        self.access_token = None
        self.session.headers.pop("Authorization", None)

    def register(self, username: str, password: str, email: str) -> requests.Response:
        """Регистрация пользователя"""
        return self.session.post(f"{self.base_url}/register", json={
            "username": username,
            "password": password,
            "email": email
        })

    def login(self, username: str, password: str) -> requests.Response:
        """Авторизация пользователя"""
        response = self.session.post(f"{self.base_url}/login", json={
            "username": username,
            "password": password
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            if token:
                self.set_auth_token(token)
        return response

    def get_profile(self) -> requests.Response:
        """Получить профиль пользователя"""
        return self.session.get(f"{self.base_url}/profile")

    def update_profile(self, **kwargs) -> requests.Response:
        """Обновить профиль пользователя"""
        return self.session.put(f"{self.base_url}/profile", json=kwargs)

    def create_post(self, title: str, description: str, is_private: bool = False,
                    tags: list = None) -> requests.Response:
        """Создать пост"""
        return self.session.post(f"{self.base_url}/posts", json={
            "title": title,
            "description": description,
            "is_private": is_private,
            "tags": tags or []
        })

    def get_post(self, post_id: str) -> requests.Response:
        """Получить пост"""
        return self.session.get(f"{self.base_url}/posts/{post_id}")

    def update_post(self, post_id: str, **kwargs) -> requests.Response:
        """Обновить пост"""
        return self.session.put(f"{self.base_url}/posts/{post_id}", json=kwargs)

    def delete_post(self, post_id: str) -> requests.Response:
        """Удалить пост"""
        return self.session.delete(f"{self.base_url}/posts/{post_id}")

    def list_posts(self, page: int = 0, page_size: int = 10) -> requests.Response:
        """Получить список постов"""
        return self.session.get(f"{self.base_url}/posts", params={
            "page": page,
            "page_size": page_size
        })

    def like_post(self, post_id: str) -> requests.Response:
        """Лайкнуть пост"""
        return self.session.post(f"{self.base_url}/posts/{post_id}/like")

    def create_comment(self, post_id: str, content: str) -> requests.Response:
        """Создать комментарий"""
        return self.session.post(f"{self.base_url}/posts/{post_id}/comments", json={
            "content": content
        })

    def list_comments(self, post_id: str, page: int = 0, page_size: int = 10) -> requests.Response:
        """Получить комментарии к посту"""
        return self.session.get(f"{self.base_url}/posts/{post_id}/comments", params={
            "page": page,
            "page_size": page_size
        })

    def get_post_stats(self, post_id: str) -> requests.Response:
        """Получить статистику поста"""
        return self.session.get(f"{self.base_url}/posts/{post_id}/stats")

    def get_post_views_history(self, post_id: str) -> requests.Response:
        """Получить историю просмотров поста"""
        return self.session.get(f"{self.base_url}/posts/{post_id}/views/history")

    def get_post_likes_history(self, post_id: str) -> requests.Response:
        """Получить историю лайков поста"""
        return self.session.get(f"{self.base_url}/posts/{post_id}/likes/history")

    def get_post_comments_history(self, post_id: str) -> requests.Response:
        """Получить историю комментариев поста"""
        return self.session.get(f"{self.base_url}/posts/{post_id}/comments/history")

    def get_recent_comments_by_minute(self, post_id: str) -> requests.Response:
        """Получить недавние комментарии по минутам"""
        return self.session.get(f"{self.base_url}/posts/{post_id}/comments/recent")

    def get_top_posts(self, sort_by: str) -> requests.Response:
        """Получить топ постов"""
        return self.session.get(f"{self.base_url}/top/posts", params={"sort_by": sort_by})

    def get_top_users(self, sort_by: str) -> requests.Response:
        """Получить топ пользователей"""
        return self.session.get(f"{self.base_url}/top/users", params={"sort_by": sort_by})


@pytest.fixture(scope="session", autouse=True)
def wait_for_services():
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{API_BASE_URL}/docs", timeout=5)
            if response.status_code == 200:
                break
        except requests.exceptions.RequestException:
            if attempt == max_attempts - 1:
                pytest.fail()
            time.sleep(2)


@pytest.fixture
def api_client():
    """Клиент для работы с API"""
    return APIClient(API_BASE_URL)


@pytest.fixture
def registered_user(api_client):
    """Зарегистрированный пользователь"""
    username = fake.user_name()
    password = fake.password()
    email = fake.email()

    response = api_client.register(username, password, email)
    assert response.status_code == 201

    return {
        "username": username,
        "password": password,
        "email": email,
        "user_data": response.json()
    }


@pytest.fixture
def authenticated_user(api_client, registered_user):
    """Авторизованный пользователь"""
    response = api_client.login(registered_user["username"], registered_user["password"])
    assert response.status_code == 200

    return {
        **registered_user,
        "token_data": response.json()
    }


@pytest.fixture
def second_authenticated_user(api_client):
    """Второй авторизованный пользователь для тестов взаимодействия"""
    username = fake.user_name()
    password = fake.password()
    email = fake.email()

    # Создаем нового клиента для второго пользователя
    second_client = APIClient(API_BASE_URL)

    # Регистрируем
    response = second_client.register(username, password, email)
    assert response.status_code == 201

    # Авторизуемся
    response = second_client.login(username, password)
    assert response.status_code == 200

    return {
        "client": second_client,
        "username": username,
        "password": password,
        "email": email,
        "user_data": response.json()
    }