```mermaid
erDiagram
    POSTS {
        int id PK "Уникальный идентификатор поста"
        int user_id "ID автора (из User Service)"
        string content "Содержимое поста"
        datetime created_at "Дата создания"
        datetime updated_at "Дата обновления"
    }
    COMMENTS {
        int id PK "Уникальный идентификатор комментария"
        int post_id FK "ID поста (если комментарий на пост)"
        int user_id "ID автора комментария"
        int parent_comment_id FK "ID родительского комментария (если есть)"
        string content "Содержимое комментария"
        datetime created_at "Дата создания"
        datetime updated_at "Дата обновления"
    }
    ATTACHMENTS {
        int id PK "Уникальный идентификатор вложения"
        int post_id FK "ID поста"
        string file_url "URL файла"
        string file_type "Тип файла"
        int file_size "Размер файла в байтах"
        datetime created_at "Дата создания"
        datetime updated_at "Дата обновления"
    }

    POSTS ||--o{ COMMENTS : ""
    POSTS ||--o{ ATTACHMENTS : ""