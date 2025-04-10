from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from .models import User
from .schemas import RegisterRequest, LoginRequest, ProfileUpdateRequest
from passlib.context import CryptContext
from .models import get_db

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/register", status_code=201)
def register_user(request: RegisterRequest, db: Session = Depends(get_db)):
    existing_username = db.query(User).filter(User.username == request.username).first()
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already exists")
    existing_email = db.query(User).filter(User.email == request.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="User with this email already exists")

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

@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username).first()
    if not user or not pwd_context.verify(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email
    }

@router.get("/profile")
def get_profile(username: str, db: Session = Depends(get_db)):
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

@router.put("/profile")
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
