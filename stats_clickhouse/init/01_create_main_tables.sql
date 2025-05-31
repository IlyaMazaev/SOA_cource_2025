CREATE TABLE IF NOT EXISTS likes (
    user_id String,
    post_id String,
    liked_at DateTime
) ENGINE = MergeTree()
ORDER BY (post_id, liked_at);

CREATE TABLE IF NOT EXISTS views (
    user_id String,
    post_id String,
    viewed_at DateTime
) ENGINE = MergeTree()
ORDER BY (post_id, viewed_at);

CREATE TABLE IF NOT EXISTS comments (
    user_id String,
    post_id String,
    comment_id String,
    content String,
    commented_at DateTime
) ENGINE = MergeTree()
ORDER BY (post_id, commented_at);