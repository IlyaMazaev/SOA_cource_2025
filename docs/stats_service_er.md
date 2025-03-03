```mermaid
erDiagram
    POST_STATISTICS {
        int id PK "Уникальный идентификатор статистики"
        int post_id "ID поста"
        int likes_count "Количество лайков"
        int views_count "Количество просмотров"
        int comments_count "Количество комментариев"
        datetime updated_at "Дата обновления статистики"
    }
    LIKE_EVENTS {
        int id PK "Уникальный идентификатор события лайка"
        int post_id "ID поста"
        int user_id "ID пользователя, поставившего лайк"
        datetime event_time "Время события"
    }
    VIEW_EVENTS {
        int id PK "Уникальный идентификатор события просмотра"
        int post_id "ID поста"
        int user_id "ID пользователя, просмотревшего пост"
        datetime event_time "Время события"
    }
    COMMENT_EVENTS {
        int id PK "Уникальный идентификатор события комментария"
        int post_id "ID поста"
        int comment_id "ID комментария"
        int user_id "ID пользователя, оставившего комментарий"
        datetime event_time "Время события"
    }

    POST_STATISTICS ||--o{ LIKE_EVENTS : ""
    POST_STATISTICS ||--o{ VIEW_EVENTS : ""
    POST_STATISTICS ||--o{ COMMENT_EVENTS : ""