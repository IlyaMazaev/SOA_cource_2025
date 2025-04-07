from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, String, Boolean, DateTime, Text
from datetime import datetime
import os
from sqlalchemy import create_engine

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


Base.metadata.create_all(bind=engine)
