import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/mini_blog",
)

KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:9092",
)

KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "comment.created")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "notification-service-group")
