CREATE TABLE IF NOT EXISTS kafka_likes (
    user_id String,
    post_id String,
    liked_at DateTime
) ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:9092',
    kafka_topic_list = 'post_likes',
    kafka_group_name = 'clickhouse-group-likes',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE TABLE IF NOT EXISTS kafka_views (
    user_id String,
    post_id String,
    viewed_at DateTime
) ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:9092',
    kafka_topic_list = 'post_views',
    kafka_group_name = 'clickhouse-group-views',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE TABLE IF NOT EXISTS kafka_comments (
    user_id String,
    post_id String,
    comment_id String,
    content String,
    commented_at DateTime
) ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:9092',
    kafka_topic_list = 'post_comments',
    kafka_group_name = 'clickhouse-group-comments',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;