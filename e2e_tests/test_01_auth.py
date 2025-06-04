import pytest
from faker import Faker

fake = Faker()


class TestAuthentication:
    def test_user_registration_success(self, api_client):
        """Тест успешной регистрации пользователя"""
        username = fake.user_name()
        password = fake.password()
        email = fake.email()

        response = api_client.register(username, password, email)

        assert response.status_code == 201
        data = response.json()
        assert "user_id" in data
        assert isinstance(data["user_id"], int)

    def test_user_registration_duplicate_username(self, api_client, registered_user):
        """Тест регистрации с дублированным именем пользователя"""
        response = api_client.register(
            registered_user["username"],
            fake.password(),
            fake.email()
        )

        # Должна быть ошибка (обычно 400 или 409)
        assert response.status_code in [400, 409]

    def test_user_login_success(self, api_client, registered_user):
        """Тест успешной авторизации"""
        response = api_client.login(
            registered_user["username"],
            registered_user["password"]
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0

    def test_user_login_invalid_credentials(self, api_client, registered_user):
        """Тест авторизации с неверными данными"""
        response = api_client.login(
            registered_user["username"],
            "wrong_password"
        )

        assert response.status_code == 401

    def test_user_login_nonexistent_user(self, api_client):
        """Тест авторизации несуществующего пользователя"""
        response = api_client.login(
            "nonexistent_user",
            "any_password"
        )

        assert response.status_code == 401


class TestProfile:
    def test_get_profile_success(self, api_client, authenticated_user):
        """Тест получения профиля авторизованного пользователя"""
        response = api_client.get_profile()

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == authenticated_user["username"]
        assert data["email"] == authenticated_user["email"]
        assert "created_at" in data
        assert "updated_at" in data

    def test_get_profile_unauthorized(self, api_client):
        """Тест получения профиля без авторизации"""
        response = api_client.get_profile()
        assert response.status_code == 403

    def test_update_profile_success(self, api_client, authenticated_user):
        """Тест обновления профиля"""
        new_first_name = fake.first_name()
        new_last_name = fake.last_name()
        new_phone = fake.phone_number()

        response = api_client.update_profile(
            first_name=new_first_name,
            last_name=new_last_name,
            phone=new_phone
        )

        assert response.status_code == 200

        profile_response = api_client.get_profile()
        assert profile_response.status_code == 200

    def test_update_profile_unauthorized(self, api_client):
        api_client.clear_auth()
        response = api_client.update_profile(first_name="Test")
        assert response.status_code == 403
