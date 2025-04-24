import os

import grpc
import httpx
import posts_pb2
import posts_pb2_grpc
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .auth import create_jwt_token, verify_jwt_token
from .schemas import (RegisterRequest, LoginRequest, ProfileUpdateRequest,
                      UpdatePostRequest, CreatePostRequest, CommentIn)
from kafka import KafkaProducer
import json
from datetime import datetime, timezone

router = APIRouter()
bearer_scheme = HTTPBearer()

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user_service:8001")
POSTS_SERVICE_ADDRESS = os.getenv("POSTS_SERVICE_ADDRESS", "posts_service:50051")

producer = KafkaProducer(
    bootstrap_servers=['kafka:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)


def get_posts_stub():
    channel = grpc.insecure_channel(POSTS_SERVICE_ADDRESS)
    stub = posts_pb2_grpc.PostServiceStub(channel)
    return stub


@router.post("/register", status_code=201)
async def register_user(req: RegisterRequest):
    """Проксируем регистрацию в User Service."""
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{USER_SERVICE_URL}/register", json=req.dict())
        if response.status_code != 201:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        result = response.json()
        producer.send('user_registrations', {
            'user_id': result['user_id'],
            'username': req.username,
            'registered_at': datetime.now(timezone.utc).isoformat()
        })
        producer.flush()
        return result


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


@router.post("/posts", status_code=201)
async def create_post(req: CreatePostRequest, credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    payload = verify_jwt_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user ID in token")

    stub = get_posts_stub()
    grpc_request = posts_pb2.CreatePostRequest(
        title=req.title,
        description=req.description,
        creator_id=user_id,
        is_private=req.is_private,
        tags=req.tags
    )
    try:
        response = stub.CreatePost(grpc_request)
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=f"gRPC error: {str(e)}")

    post = response.post
    return {
        "id": post.id,
        "title": post.title,
        "description": post.description,
        "creator_id": post.creator_id,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
        "is_private": post.is_private,
        "tags": list(post.tags)
    }


@router.get("/posts/{post_id}")
async def get_post(post_id: str, credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    payload = verify_jwt_token(credentials.credentials)
    user_id = payload.get("sub")
    stub = get_posts_stub()
    grpc_request = posts_pb2.GetPostRequest(id=post_id)
    try:
        response = stub.GetPost(grpc_request, metadata=(("current_user", user_id),))
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=404, detail="Post not found")
        raise HTTPException(status_code=500, detail=f"gRPC error: {str(e)}")
    post = response.post
    return {
        "id": post.id,
        "title": post.title,
        "description": post.description,
        "creator_id": post.creator_id,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
        "is_private": post.is_private,
        "tags": list(post.tags)
    }


@router.put("/posts/{post_id}")
async def update_post(post_id: str, req: UpdatePostRequest,
                      credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    payload = verify_jwt_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user ID in token")

    stub = get_posts_stub()
    try:
        get_response = stub.GetPost(posts_pb2.GetPostRequest(id=post_id), metadata=(("current_user", user_id),))
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=404, detail="Post not found")
        raise HTTPException(status_code=500, detail=f"gRPC error: {str(e)}")

    post = get_response.post
    if post.creator_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this post")

    updated_title = req.title if req.title is not None else post.title
    updated_description = req.description if req.description is not None else post.description
    updated_is_private = req.is_private if req.is_private is not None else post.is_private
    updated_tags = req.tags if req.tags is not None else list(post.tags)

    grpc_request = posts_pb2.UpdatePostRequest(
        id=post_id,
        title=updated_title,
        description=updated_description,
        is_private=updated_is_private,
        tags=updated_tags
    )
    try:
        response = stub.UpdatePost(grpc_request, metadata=(("current_user", user_id),))
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=404, detail="Post not found")
        raise HTTPException(status_code=500, detail=f"gRPC error: {str(e)}")
    updated_post = response.post
    return {
        "id": updated_post.id,
        "title": updated_post.title,
        "description": updated_post.description,
        "creator_id": updated_post.creator_id,
        "created_at": updated_post.created_at,
        "updated_at": updated_post.updated_at,
        "is_private": updated_post.is_private,
        "tags": list(updated_post.tags)
    }


@router.delete("/posts/{post_id}")
async def delete_post(post_id: str, credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    payload = verify_jwt_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user ID in token")

    stub = get_posts_stub()

    try:
        get_response = stub.GetPost(posts_pb2.GetPostRequest(id=post_id), metadata=(("current_user", user_id),))
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=404, detail="Post not found")
        raise HTTPException(status_code=500, detail=f"gRPC error: {str(e)}")

    post = get_response.post
    if post.creator_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")

    grpc_request = posts_pb2.DeletePostRequest(id=post_id)
    try:
        response = stub.DeletePost(grpc_request, metadata=(("current_user", user_id),))
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=404, detail="Post not found")
        raise HTTPException(status_code=500, detail=f"gRPC error: {str(e)}")

    return {"detail": response.message}


@router.get("/posts")
async def list_posts(page: int = 0, page_size: int = 10,
                     credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    verify_jwt_token(credentials.credentials)
    stub = get_posts_stub()
    grpc_request = posts_pb2.ListPostsRequest(page=page, page_size=page_size)
    try:
        response = stub.ListPosts(grpc_request)
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=f"gRPC error: {str(e)}")

    posts_list = []
    for post in response.posts:
        posts_list.append({
            "id": post.id,
            "title": post.title,
            "description": post.description,
            "creator_id": post.creator_id,
            "created_at": post.created_at,
            "updated_at": post.updated_at,
            "is_private": post.is_private,
            "tags": list(post.tags)
        })
    return posts_list


@router.post("/posts/{post_id}/view")
async def view_post(post_id: str, credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    payload = verify_jwt_token(credentials.credentials)
    user_id = payload.get("sub")
    stub = get_posts_stub()
    try:
        resp = stub.ViewPost(
            posts_pb2.ViewRequest(post_id=post_id, user_id=user_id),
            metadata=(('current_user', user_id),)
        )
    except grpc.RpcError as e:
        status = e.code()
        if status == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=404, detail="Post not found")
        if status == grpc.StatusCode.PERMISSION_DENIED:
            raise HTTPException(status_code=403, detail="Access denied: private post")
        detail = e.details() if hasattr(e, 'details') else str(e)
        raise HTTPException(status_code=500, detail=detail)
    return {'message': resp.message}


@router.post("/posts/{post_id}/like")
async def like_post(post_id: str, credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    payload = verify_jwt_token(credentials.credentials)
    user_id = payload.get("sub")
    stub = get_posts_stub()
    try:
        resp = stub.LikePost(
            posts_pb2.LikeRequest(post_id=post_id, user_id=user_id),
            metadata=(('current_user', user_id),)
        )
    except grpc.RpcError as e:
        if not hasattr(e, 'code'):
            raise HTTPException(status_code=500, detail=f"gRPC error: {str(e)}")
        status = e.code()
        if status == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=404, detail="Post not found")
        if status == grpc.StatusCode.ALREADY_EXISTS:
            raise HTTPException(status_code=409, detail="Post already liked")
        detail = e.details() if hasattr(e, 'details') else str(e)
        raise HTTPException(status_code=500, detail=detail)
    return {'message': resp.message}


@router.post("/posts/{post_id}/comments")
async def create_comment(post_id: str, body: CommentIn,
                         credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    payload = verify_jwt_token(credentials.credentials)
    user_id = payload.get("sub")
    stub = get_posts_stub()
    try:
        resp = stub.CreateComment(
            posts_pb2.CreateCommentRequest(
                post_id=post_id,
                user_id=user_id,
                content=body.content
            ),
            metadata=(('current_user', user_id),)
        )
    except grpc.RpcError as e:
        status = e.code()
        if status == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=404, detail="Post not found")
        if status == grpc.StatusCode.PERMISSION_DENIED:
            raise HTTPException(status_code=403, detail="Access denied: private post")
        detail = e.details() if hasattr(e, 'details') else str(e)
        raise HTTPException(status_code=500, detail=detail)
    return {
        'id': resp.comment.id,
        'post_id': resp.comment.post_id,
        'user_id': resp.comment.user_id,
        'content': resp.comment.content,
        'created_at': resp.comment.created_at
    }


@router.get("/posts/{post_id}/comments")
async def list_comments(
        post_id: str,
        page: int = 0,
        page_size: int = 10,
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
):
    payload = verify_jwt_token(credentials.credentials)
    user_id = payload.get("sub")
    stub = get_posts_stub()
    try:
        resp = stub.ListComments(
            posts_pb2.ListCommentsRequest(
                post_id=post_id,
                page=page,
                page_size=page_size
            ),
            metadata=(('current_user', user_id),)
        )
    except grpc.RpcError as e:
        status = e.code()
        if status == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=404, detail="Post not found")
        if status == grpc.StatusCode.PERMISSION_DENIED:
            raise HTTPException(status_code=403, detail="Access denied: private post")
        detail = e.details() if hasattr(e, 'details') else str(e)
        raise HTTPException(status_code=500, detail=detail)

    comments_list = []
    for comment in resp.comments:
        comments_list.append({
            'id': comment.id,
            'post_id': comment.post_id,
            'user_id': comment.user_id,
            'content': comment.content,
            'created_at': comment.created_at
        })
    return comments_list
