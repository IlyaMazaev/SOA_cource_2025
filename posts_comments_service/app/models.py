from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
from datetime import datetime
import os
from sqlalchemy import create_engine
import uuid

DATABASE_URL = os.getenv("POSTS_DB_URL", "postgresql://posts_user:posts_password@posts_db:5432/posts_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Post(Base):
    __tablename__ = "posts"
    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    creator_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_private = Column(Boolean, default=False)
    tags = Column(Text, default="")


class Comment(Base):
    __tablename__ = 'comments'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(String, ForeignKey('posts.id'), nullable=False)
    user_id = Column(String, nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class PostLike(Base):
    __tablename__ = 'post_likes'
    user_id = Column(String, primary_key=True)
    post_id = Column(String, ForeignKey('posts.id'), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('user_id', 'post_id', name='uq_user_post_like'),)


Base.metadata.create_all(bind=engine)
