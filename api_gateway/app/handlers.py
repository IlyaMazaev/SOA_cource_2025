import os
import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .schemas import RegisterRequest, LoginRequest, ProfileUpdateRequest
from .auth import create_jwt_token, verify_jwt_token

router = APIRouter()
bearer_scheme = HTTPBearer()

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user_service:8001")

@router.post("/register", status_code=201)
async def register_user(req: RegisterRequest):
    """Проксируем регистрацию в User Service."""
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{USER_SERVICE_URL}/register", json=req.dict())
        if response.status_code != 201:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()

@router.post("/login")
async def login(req: LoginRequest):
    """Проксируем логин в User Service и генерируем JWT при успешной аутентификации."""
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{USER_SERVICE_URL}/login", json=req.dict())
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        user_data = response.json()
        token = create_jwt_token(
            username=user_data["username"],
            user_id=user_data["user_id"],
            email=user_data["email"]
        )
        return {"access_token": token, "token_type": "bearer"}

@router.get("/profile")
async def get_profile(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    """
    Проверяем JWT, достаем username и проксируем запрос в User Service для получения профиля.
    """
    payload = verify_jwt_token(credentials.credentials)
    username = payload.get("sub")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{USER_SERVICE_URL}/profile", params={"username": username})
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()

@router.put("/profile")
async def update_profile(
    req: ProfileUpdateRequest,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
):
    """
    Проверяем JWT, достаем username и проксируем запрос в User Service для обновления профиля.
    """
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
