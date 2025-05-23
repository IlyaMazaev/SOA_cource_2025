CREATE MATERIALIZED VIEW IF NOT EXISTS mv_likes TO likes AS
SELECT user_id, post_id, liked_at
FROM kafka_likes;

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_views TO views AS
SELECT user_id, post_id, viewed_at
FROM kafka_views;

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_comments TO comments AS
SELECT user_id, post_id, comment_id, content, commented_at
FROM kafka_comments;