from pydantic import BaseModel, EmailStr, constr
from typing import Optional
from datetime import date

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
