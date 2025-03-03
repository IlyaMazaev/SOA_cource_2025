from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, constr
from typing import Optional
from datetime import datetime, date
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Date
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from passlib.context import CryptContext

DATABASE_URL = "postgresql://user:password@user_db:5432/users_db"
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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

Base.metadata.create_all(bind=engine)

app = FastAPI(title="User Service")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----- Pydantic модели -----

class RegisterRequest(BaseModel):
    username: constr(min_length=3)
    password: constr(min_length=5)
    email: EmailStr

class LoginRequest(BaseModel):
    username: str
    password: str

class ProfileUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birth_date: Optional[date] = None
    mail: Optional[EmailStr] = None
    phone: Optional[str] = None

# ----- Маршруты -----

@app.post("/register", status_code=201)
def register_user(request: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == request.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_password = pwd_context.hash(request.password)
    new_user = User(
        username=request.username,
        email=request.email,
        password_hash=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created", "user_id": new_user.id}

@app.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username).first()
    if not user or not pwd_context.verify(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Возвращаем простую информацию о пользователе
    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email
    }

@app.get("/profile")
def get_profile(username: str, db: Session = Depends(get_db)):
    # username передаётся прокси-сервисом после проверки JWT
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "birth_date": user.birth_date,
        "mail": user.mail,
        "phone": user.phone,
        "created_at": user.created_at,
        "updated_at": user.updated_at
    }

@app.put("/profile")
def update_profile(username: str, req: ProfileUpdateRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if req.first_name is not None:
        user.first_name = req.first_name
    if req.last_name is not None:
        user.last_name = req.last_name
    if req.birth_date is not None:
        user.birth_date = req.birth_date
    if req.mail is not None:
        user.mail = req.mail
    if req.phone is not None:
        user.phone = req.phone

    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return {"message": "Profile updated"}
