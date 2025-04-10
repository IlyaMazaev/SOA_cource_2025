import grpc
from concurrent import futures
import time
import uuid
import datetime

import posts_pb2
import posts_pb2_grpc

from sqlalchemy.exc import SQLAlchemyError
from .models import Post, SessionLocal


def post_to_proto(post: Post) -> posts_pb2.Post:
    return posts_pb2.Post(
        id=post.id,
        title=post.title,
        description=post.description,
        creator_id=post.creator_id,
        created_at=post.created_at.isoformat(),
        updated_at=post.updated_at.isoformat(),
        is_private=post.is_private,
        tags=post.tags.split(",") if post.tags else []
    )


class PostService(posts_pb2_grpc.PostServiceServicer):
    def CreatePost(self, request, context):
        session = SessionLocal()
        try:
            post_id = str(uuid.uuid4())
            now = datetime.datetime.utcnow()
            tags_str = ",".join(request.tags)
            new_post = Post(
                id=post_id,
                title=request.title,
                description=request.description,
                creator_id=request.creator_id,
                created_at=now,
                updated_at=now,
                is_private=request.is_private,
                tags=tags_str
            )
            session.add(new_post)
            session.commit()
            session.refresh(new_post)
            return posts_pb2.CreatePostResponse(post=post_to_proto(new_post))
        except SQLAlchemyError as e:
            session.rollback()
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Database error: {str(e)}")
            return posts_pb2.CreatePostResponse()
        finally:
            session.close()

    def GetPost(self, request, context):
        session = SessionLocal()
        try:
            post = session.query(Post).filter(Post.id == request.id).first()
            if post is None:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details('Post not found')
                return posts_pb2.GetPostResponse()

            if post.is_private:
                current_user = dict(context.invocation_metadata()).get("current_user")
                if current_user != post.creator_id:
                    context.set_code("PERMISSION_DENIED")
                    context.set_details(f"Access denied: private post, {current_user} != {post.creator_id}")
                    return posts_pb2.GetPostResponse()

            return posts_pb2.GetPostResponse(post=post_to_proto(post))
        except SQLAlchemyError as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Database error: {str(e)}")
            return posts_pb2.GetPostResponse()
        finally:
            session.close()

    def UpdatePost(self, request, context):
        session = SessionLocal()
        try:
            post = session.query(Post).filter(Post.id == request.id).first()
            if post is None:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details('Post not found')
                return posts_pb2.UpdatePostResponse()
            current_user = dict(context.invocation_metadata()).get("current_user")
            if current_user != post.creator_id:
                context.set_code("PERMISSION_DENIED")
                context.set_details("Access denied: not the owner")
                return posts_pb2.UpdatePostResponse()
            if request.title:
                post.title = request.title
            if request.description:
                post.description = request.description
            post.updated_at = datetime.datetime.utcnow()
            post.is_private = request.is_private
            post.tags = ",".join(request.tags)
            session.commit()
            session.refresh(post)
            return posts_pb2.UpdatePostResponse(post=post_to_proto(post))
        except SQLAlchemyError as e:
            session.rollback()
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Database error: {str(e)}")
            return posts_pb2.UpdatePostResponse()
        finally:
            session.close()

    def DeletePost(self, request, context):
        session = SessionLocal()
        try:
            post = session.query(Post).filter(Post.id == request.id).first()
            if post:
                current_user = dict(context.invocation_metadata()).get("current_user")
                if current_user != post.creator_id:
                    context.set_code("PERMISSION_DENIED")
                    context.set_details("Access denied: not the owner")
                    return posts_pb2.DeletePostResponse()
                session.delete(post)
                session.commit()
                return posts_pb2.DeletePostResponse(message="Post deleted")
            else:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details('Post not found')
                return posts_pb2.DeletePostResponse()
        except SQLAlchemyError as e:
            session.rollback()
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Database error: {str(e)}")
            return posts_pb2.DeletePostResponse()
        finally:
            session.close()

    def ListPosts(self, request, context):
        session = SessionLocal()
        try:
            current_user = dict(context.invocation_metadata()).get("current_user")
            query = session.query(Post)
            if current_user:
                query = query.filter((Post.is_private == False) | (Post.creator_id == current_user))
            else:
                query = query.filter(Post.is_private == False)

            posts_list = query.offset(request.page * request.page_size).limit(request.page_size).all()
            proto_posts = [post_to_proto(p) for p in posts_list]
            return posts_pb2.ListPostsResponse(posts=proto_posts)
        except SQLAlchemyError as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Database error: {str(e)}")
            return posts_pb2.ListPostsResponse()
        finally:
            session.close()


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    posts_pb2_grpc.add_PostServiceServicer_to_server(PostService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()
