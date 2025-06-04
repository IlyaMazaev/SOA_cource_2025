import pytest
from faker import Faker

fake = Faker()


class TestPosts:
    def test_create_post_success(self, api_client, authenticated_user):
        """Тест создания поста"""
        title = fake.sentence()
        description = fake.text()
        tags = [fake.word(), fake.word()]

        response = api_client.create_post(title, description, False, tags)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == title
        assert data["description"] == description
        assert data["is_private"] == False
        assert set(data["tags"]) == set(tags)
        assert "id" in data
        assert "created_at" in data
        assert "creator_id" in data

    def test_create_private_post(self, api_client, authenticated_user):
        """Тест создания приватного поста"""
        title = fake.sentence()
        description = fake.text()

        response = api_client.create_post(title, description, True)

        assert response.status_code == 201
        data = response.json()
        assert data["is_private"] == True

    def test_create_post_unauthorized(self, api_client):
        """Тест создания поста без авторизации"""
        api_client.clear_auth()

        response = api_client.create_post("Title", "Description")

        assert response.status_code == 403

    def test_get_post_success(self, api_client, authenticated_user):
        """Тест получения поста"""
        create_response = api_client.create_post(fake.sentence(), fake.text())
        assert create_response.status_code == 201
        post_id = create_response.json()["id"]

        response = api_client.get_post(post_id)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == post_id
        assert "title" in data
        assert "description" in data

    def test_get_nonexistent_post(self, api_client, authenticated_user):
        """Тест получения несуществующего поста"""
        response = api_client.get_post("nonexistent-id")

        assert response.status_code == 404

    def test_update_own_post(self, api_client, authenticated_user):
        """Тест обновления своего поста"""
        create_response = api_client.create_post(fake.sentence(), fake.text())
        assert create_response.status_code == 201
        post_id = create_response.json()["id"]

        new_title = fake.sentence()
        new_description = fake.text()
        response = api_client.update_post(post_id, title=new_title, description=new_description)

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == new_title
        assert data["description"] == new_description

    def test_update_post_unauthorized(self, api_client, authenticated_user):
        """Тест обновления поста без авторизации"""
        create_response = api_client.create_post(fake.sentence(), fake.text())
        assert create_response.status_code == 201
        post_id = create_response.json()["id"]

        api_client.clear_auth()
        response = api_client.update_post(post_id, title="New Title")

        assert response.status_code == 403

    def test_delete_own_post(self, api_client, authenticated_user):
        """Тест удаления своего поста"""
        create_response = api_client.create_post(fake.sentence(), fake.text())
        assert create_response.status_code == 201
        post_id = create_response.json()["id"]

        response = api_client.delete_post(post_id)

        assert response.status_code == 200

        get_response = api_client.get_post(post_id)
        assert get_response.status_code == 404

    def test_delete_post_unauthorized(self, api_client, authenticated_user):
        """Тест удаления поста без авторизации"""
        create_response = api_client.create_post(fake.sentence(), fake.text())
        assert create_response.status_code == 201
        post_id = create_response.json()["id"]

        api_client.clear_auth()
        response = api_client.delete_post(post_id)

        assert response.status_code == 403

    def test_list_posts(self, api_client, authenticated_user):
        """Тест получения списка постов"""
        for _ in range(3):
            response = api_client.create_post(fake.sentence(), fake.text())
            assert response.status_code == 201

        response = api_client.list_posts()

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3

        if data:
            post = data[0]
            assert "id" in post
            assert "title" in post
            assert "description" in post
            assert "creator_id" in post

    def test_list_posts_pagination(self, api_client, authenticated_user):
        """Тест пагинации списка постов"""
        for _ in range(5):
            response = api_client.create_post(fake.sentence(), fake.text())
            assert response.status_code == 201

        response = api_client.list_posts(page=0, page_size=2)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 2

    def test_access_private_post_by_owner(self, api_client, authenticated_user):
        """Тест доступа к приватному посту владельцем"""
        create_response = api_client.create_post(fake.sentence(), fake.text(), is_private=True)
        assert create_response.status_code == 201
        post_id = create_response.json()["id"]

        response = api_client.get_post(post_id)
        assert response.status_code == 200

    def test_access_private_post_by_other_user(self, api_client, authenticated_user, second_authenticated_user):
        """Тест доступа к приватному посту другим пользователем"""
        create_response = api_client.create_post(fake.sentence(), fake.text(), is_private=True)
        assert create_response.status_code == 201
        post_id = create_response.json()["id"]

        response = second_authenticated_user["client"].get_post(post_id)
        assert response.status_code == 500

    def test_update_other_user_post(self, api_client, authenticated_user, second_authenticated_user):
        """Тест попытки обновления чужого поста"""
        create_response = api_client.create_post(fake.sentence(), fake.text())
        assert create_response.status_code == 201
        post_id = create_response.json()["id"]

        response = second_authenticated_user["client"].update_post(post_id, title="Hacked!")
        assert response.status_code == 403

    def test_delete_other_user_post(self, api_client, authenticated_user, second_authenticated_user):
        """Тест попытки удаления чужого поста"""
        create_response = api_client.create_post(fake.sentence(), fake.text())
        assert create_response.status_code == 201
        post_id = create_response.json()["id"]

        response = second_authenticated_user["client"].delete_post(post_id)
        assert response.status_code == 403