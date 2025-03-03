# proxy_service/main.py
from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import os
import jwt
from datetime import datetime, timedelta
from pydantic import BaseModel

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "SUPER_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user_service:8001")

app = FastAPI(title="API Gateway")

# Для чтения токена из заголовка
bearer_scheme = HTTPBearer()

# ----- Утилиты для работы с JWT -----

def create_jwt_token(username: str, user_id: int, email: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": username,
        "user_id": user_id,
        "email": email,
        "exp": expire
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token

def verify_jwt_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ----- Pydantic модели -----

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str

class LoginRequest(BaseModel):
    username: str
    password: str

class ProfileUpdateRequest(BaseModel):
    first_name: str = None
    last_name: str = None
    birth_date: str = None
    mail: str = None
    phone: str = None

# ----- Маршруты -----

@app.post("/register")
async def register_user(req: RegisterRequest):
    """ Проксируем регистрацию в User Service """
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{USER_SERVICE_URL}/register", json=req.dict())
        if response.status_code != 201:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()

@app.post("/login")
async def login(req: LoginRequest):
    """ Проксируем логин в User Service, если успех — генерируем JWT """
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{USER_SERVICE_URL}/login", json=req.dict())
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        user_data = response.json()
        # user_data = { "user_id": 123, "username": "...", "email": "..." }

        token = create_jwt_token(
            username=user_data["username"],
            user_id=user_data["user_id"],
            email=user_data["email"]
        )
        return {"access_token": token, "token_type": "bearer"}

@app.get("/profile")
async def get_profile(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    """
    Проверяем JWT, достаем username из payload,
    проксируем запрос в User Service, передавая username как query-param.
    """
    payload = verify_jwt_token(credentials.credentials)
    username = payload.get("sub")  # sub = username

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{USER_SERVICE_URL}/profile", params={"username": username})
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()

@app.put("/profile")
async def update_profile(
    req: ProfileUpdateRequest,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
):
    """ Аналогично get_profile, но используем PUT """
    payload = verify_jwt_token(credentials.credentials)
    username = payload.get("sub")

    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{USER_SERVICE_URL}/profile",
            params={"username": username},
            json=req.dict()
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()
