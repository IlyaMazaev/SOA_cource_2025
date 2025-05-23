import grpc
from concurrent import futures

import stats_pb2
import stats_pb2_grpc
import os

import clickhouse_connect

CLICKHOUSE_USER_NAME = os.getenv("CLICKHOUSE_USER_NAME", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB", "default")

client = clickhouse_connect.get_client(host='stats_clickhouse',
                                       port=8123,
                                       username=CLICKHOUSE_USER_NAME,
                                       password=CLICKHOUSE_PASSWORD,
                                       database=CLICKHOUSE_DB
                                       )


class StatsService(stats_pb2_grpc.StatsServiceServicer):
    def GetPostStats(self, request, context):
        try:
            likes_result = client.query(f"SELECT count() FROM likes WHERE post_id = '{request.post_id}'")
            likes = likes_result.result_rows[0][0]

            views_result = client.query(f"SELECT count() FROM views WHERE post_id = '{request.post_id}'")
            views = views_result.result_rows[0][0]

            comments_result = client.query(f"SELECT count() FROM comments WHERE post_id = '{request.post_id}'")
            comments = comments_result.result_rows[0][0]

            return stats_pb2.PostStatsResponse(views=views, likes=likes, comments=comments)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Database error: {str(e)}")
            return stats_pb2.PostStatsResponse()

    def _get_daily_stats(self, table, post_id):
        time_col = {'views': 'viewed_at', 'likes': 'liked_at', 'comments': 'commented_at'}
        query = f"""
        SELECT toDate({time_col[table]}) as date, count() as stat
        FROM {table}
        WHERE post_id = '{post_id}'
        GROUP BY date
        ORDER BY date
        """
        result = client.query(query)
        return [stats_pb2.DayStats(date=row[0].strftime('%Y-%m-%d'), stat=row[1]) for row in result.result_rows]

    def GetPostViewsHistory(self, request, context):
        try:
            history = self._get_daily_stats("views", request.post_id)
            return stats_pb2.PostHistoryResponse(history=history)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Database error: {str(e)}")
            return stats_pb2.PostHistoryResponse()

    def GetPostLikesHistory(self, request, context):
        try:
            history = self._get_daily_stats("likes", request.post_id)
            return stats_pb2.PostHistoryResponse(history=history)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Database error: {str(e)}")
            return stats_pb2.PostHistoryResponse()

    def GetPostCommentsHistory(self, request, context):
        try:
            history = self._get_daily_stats("comments", request.post_id)
            return stats_pb2.PostHistoryResponse(history=history)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Database error: {str(e)}")
            return stats_pb2.PostHistoryResponse()

    def GetPostRecentComments(self, request, context):
        try:
            query = f"""
                SELECT toStartOfMinute(commented_at) as minute, count() as stat
                FROM comments
                WHERE post_id = '{request.post_id}' AND commented_at > now() - INTERVAL 1 HOUR
                GROUP BY minute
                ORDER BY minute
                """
            result = client.query(query)
            history = [
                stats_pb2.DayStats(date=minute.strftime('%Y-%m-%d %H:%M'), stat=stat)
                for minute, stat in result.result_rows
            ]
            return stats_pb2.PostHistoryResponse(history=history)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Database error: {str(e)}")
            return stats_pb2.PostHistoryResponse()

    def GetTopTenPosts(self, request, context):
        param_map = {
            stats_pb2.VIEWS: "views",
            stats_pb2.LIKES: "likes",
            stats_pb2.COMMENTS: "comments"
        }
        table = param_map[request.param]
        try:
            query = f"""
            SELECT post_id, count() as cnt
            FROM {table}
            GROUP BY post_id
            ORDER BY cnt DESC
            LIMIT 10
            """
            result = client.query(query)
            post_ids = [row[0] for row in result.result_rows]
            return stats_pb2.TopTenPostsResponse(post_ids=post_ids)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Database error: {str(e)}")
            return stats_pb2.TopTenPostsResponse()

    def GetTopTenUsers(self, request, context):
        param_map = {
            stats_pb2.VIEWS: "views",
            stats_pb2.LIKES: "likes",
            stats_pb2.COMMENTS: "comments"
        }
        table = param_map[request.param]
        try:
            query = f"""
            SELECT user_id, count() as cnt
            FROM {table}
            GROUP BY user_id
            ORDER BY cnt DESC
            LIMIT 10
            """
            result = client.query(query)
            user_ids = [row[0] for row in result.result_rows]
            return stats_pb2.TopTenUsersResponse(user_ids=user_ids)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Database error: {str(e)}")
            return stats_pb2.TopTenUsersResponse()


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    stats_pb2_grpc.add_StatsServiceServicer_to_server(StatsService(), server)
    server.add_insecure_port('[::]:50050')
    server.start()
    server.wait_for_termination()
