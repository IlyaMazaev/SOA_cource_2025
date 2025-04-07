## Для запуска тестов достаточно выполнить pytest в корне контейнера каждого из сервисов


## Curl запросы для тестирования:

### Регистрация пользователя

```
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{
        "username": "testuser",
        "password": "secret123",
        "email": "test@example.com"
      }'
```

### Логин 

```
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{
        "username": "testuser",
        "password": "secret123"
      }'
```

### Получение профиля

```
curl -X GET http://localhost:8000/profile \
  -H "Authorization: Bearer <access_token>"

```

### Обновление данных

```
curl -X PUT "http://localhost:8000/profile?username=testuser" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
        "first_name": "John",
        "last_name": "Doe",
        "mail": "john.doe@example.com",
        "phone": "1234567890"
      }'
```


### Повторное получение профиля с новыми данными

```
curl -X GET http://localhost:8000/profile \
  -H "Authorization: Bearer <access_token>"

```

## Curl запросы для тестирования сервиса постов

### Добавление поста

```
curl -X POST http://localhost:8000/posts \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer <access_token>" \
    -d '{
        "title": "Test Post",
        "description": "This is a test post",
        "is_private": false,
        "tags": ["test", "api"]
    }'
```

### Получение поста по ID
```
curl -X GET http://localhost:8000/posts/<post_id> \
-H "Authorization: Bearer <access_token>"
```

### Изменение поста

```
curl -X PUT http://localhost:8000/posts/<post_id> \
    -H "Content-Type: application/json"  \
    -H "Authorization: Bearer <access_token>" \ 
    -d '{
        "title": "Updated Test Post",
        "description": "Updated description",
        "is_private": false,
        "tags": ["updated", "api"]
    }'
```


### пример тестирования:

![alt text](curl_test_screenshot.png)