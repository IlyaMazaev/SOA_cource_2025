import pytest
from faker import Faker

fake = Faker()


class TestPostInteractions:
    def test_like_post_success(self, api_client, authenticated_user):
        """Тест успешного лайка поста"""
        create_response = api_client.create_post(fake.sentence(), fake.text())
        assert create_response.status_code == 201
        post_id = create_response.json()["id"]

        response = api_client.like_post(post_id)

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_like_nonexistent_post(self, api_client, authenticated_user):
        """Тест лайка несуществующего поста"""
        response = api_client.like_post("nonexistent-id")

        assert response.status_code == 404

    def test_like_post_unauthorized(self, api_client, authenticated_user):
        """Тест лайка поста без авторизации"""
        create_response = api_client.create_post(fake.sentence(), fake.text())
        assert create_response.status_code == 201
        post_id = create_response.json()["id"]

        api_client.clear_auth()
        response = api_client.like_post(post_id)

        assert response.status_code == 403

    def test_like_private_post_by_other_user(self, api_client, authenticated_user, second_authenticated_user):
        """Тест лайка приватного поста другим пользователем"""
        create_response = api_client.create_post(fake.sentence(), fake.text(), is_private=True)
        assert create_response.status_code == 201
        post_id = create_response.json()["id"]

        response = second_authenticated_user["client"].like_post(post_id)
        assert response.status_code == 500

    def test_double_like_post(self, api_client, authenticated_user):
        """Тест повторного лайка поста"""
        create_response = api_client.create_post(fake.sentence(), fake.text())
        assert create_response.status_code == 201
        post_id = create_response.json()["id"]

        response1 = api_client.like_post(post_id)
        assert response1.status_code == 200

        response2 = api_client.like_post(post_id)
        assert response2.status_code == 409


class TestComments:
    def test_create_comment_success(self, api_client, authenticated_user):
        """Тест создания комментария"""
        create_response = api_client.create_post(fake.sentence(), fake.text())
        assert create_response.status_code == 201
        post_id = create_response.json()["id"]

        comment_content = fake.text()
        response = api_client.create_comment(post_id, comment_content)

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == comment_content
        assert data["post_id"] == post_id
        assert "id" in data
        assert "user_id" in data
        assert "created_at" in data

    def test_create_comment_nonexistent_post(self, api_client, authenticated_user):
        """Тест создания комментария к несуществующему посту"""
        response = api_client.create_comment("nonexistent-id", fake.text())

        assert response.status_code == 404

    def test_create_comment_unauthorized(self, api_client, authenticated_user):
        """Тест создания комментария без авторизации"""
        create_response = api_client.create_post(fake.sentence(), fake.text())
        assert create_response.status_code == 201
        post_id = create_response.json()["id"]

        api_client.clear_auth()
        response = api_client.create_comment(post_id, fake.text())

        assert response.status_code == 403
