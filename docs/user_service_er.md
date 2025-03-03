```mermaid
erDiagram
    USERS {
        int id PK "Уникальный идентификатор пользователя"
        string username "Имя пользователя"
        string email "Email пользователя"
        string password_hash "Хэш пароля"
        datetime created_at "Дата регистрации"
        datetime updated_at "Дата обновления"
        string avatar_url "URL аватара"
    }
    SUBSCRIPTIONS {
        int id PK "Уникальный идентификатор подписки"
        int follower_id FK "ID подписчика (пользователь)"
        int following_id FK "ID подписанного (пользователь)"
        datetime subscribed_at "Дата подписки"
    }
    USER_SETTINGS {
        int id PK "Уникальный идентификатор настроек"
        int user_id FK "ID пользователя"
        boolean email_notifications "Уведомления по email включены"
        string language "Язык интерфейса"
        string theme "Тема оформления"
        boolean is_profile_private "Приватный профиль"
        datetime updated_at "Дата обновления настроек"
    }
    USER_PROFILE {
        int id PK "Уникальный идентификатор профиля"
        int user_id FK "ID пользователя"
        string about "О себе"
        string work "Место работы"
        date birthday "Дата рождения"
        string city "Город"
        string relationship_status "Семейное положение"
        string education "Образование"
        string interests "Интересы"
    }
    
    USERS ||--|| USER_SETTINGS : ""
    USERS ||--|| USER_PROFILE : ""
    USERS ||--o{ SUBSCRIPTIONS : ""