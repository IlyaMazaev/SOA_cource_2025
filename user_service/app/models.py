from sqlalchemy import Column, Integer, String, DateTime, Date
from datetime import datetime
from sqlalchemy.orm import declarative_base, sessionmaker
import os
from sqlalchemy import create_engine

DATABASE_URL = os.getenv("USER_DB_URL", "postgresql://user:password@user_db:5432/users_db")

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    birth_date = Column(Date, nullable=True)
    mail = Column(String)
    phone = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
