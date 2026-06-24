from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CommunityPost, CommunityPostBookmark
from .serializers import CommunityPostSerializer, CommunityPostWriteSerializer


DEFAULT_LIST_LIMIT = 50
MAX_LIST_LIMIT = 100

ERROR_MESSAGES = {
    "AUTHENTICATION_REQUIRED": "Authentication is required.",
    "COMMUNITY_POST_NOT_FOUND": "Community post was not found.",
    "COMMUNITY_POST_FORBIDDEN": "Only the author can modify this community post.",
    "INVALID_COMMUNITY_POST": "Community post input is invalid.",
}


def error_response(code, http_status, details=None):
    return Response(
        {
            "code": code,
            "message": ERROR_MESSAGES[code],
            "details": details,
        },
        status=http_status,
    )


def _parse_limit(raw_limit):
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        return DEFAULT_LIST_LIMIT
    if limit < 1:
        return DEFAULT_LIST_LIMIT
    return min(limit, MAX_LIST_LIMIT)


def _parse_starred(raw_value):
    return str(raw_value or "").strip().casefold() in {"1", "true", "yes", "on"}


def _post_has_exact_tag(post, tag):
    normalized_tag = tag.casefold()
    return any(isinstance(item, str) and item.casefold() == normalized_tag for item in post.tags)


def _post_matches_query(post, query):
    normalized_query = query.casefold()
    if normalized_query in post.title.casefold() or normalized_query in post.content.casefold():
        return True
    return any(isinstance(item, str) and normalized_query in item.casefold() for item in post.tags)


def _post_passes_filters(post, query, tag):
    if query and not _post_matches_query(post, query):
        return False
    if tag and not _post_has_exact_tag(post, tag):
        return False
    return True


def _starred_post_ids_for_posts(user, posts):
    if not user or not user.is_authenticated or not posts:
        return set()
    return set(
        CommunityPostBookmark.objects.filter(
            user=user,
            post_id__in=[post.id for post in posts],
        ).values_list("post_id", flat=True)
    )


class CommunityPostListCreateAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = (request.query_params.get("query") or "").strip()
        tag = (request.query_params.get("tag") or "").strip()
        limit = _parse_limit(request.query_params.get("limit"))
        starred_only = _parse_starred(request.query_params.get("starred"))

        if starred_only and (not request.user or not request.user.is_authenticated):
            return error_response("AUTHENTICATION_REQUIRED", status.HTTP_403_FORBIDDEN)

        if starred_only:
            posts = []
            starred_post_ids = set()
            bookmarks = CommunityPostBookmark.objects.select_related("post", "post__author").filter(user=request.user)
            for bookmark in bookmarks.iterator():
                post = bookmark.post
                if not _post_passes_filters(post, query, tag):
                    continue
                posts.append(post)
                starred_post_ids.add(post.id)
                if len(posts) >= limit:
                    break
        else:
            queryset = CommunityPost.objects.select_related("author").all()
            if query or tag:
                posts = []
                for post in queryset.iterator():
                    if not _post_passes_filters(post, query, tag):
                        continue
                    posts.append(post)
                    if len(posts) >= limit:
                        break
            else:
                posts = list(queryset[:limit])
            starred_post_ids = _starred_post_ids_for_posts(request.user, posts)

        serializer = CommunityPostSerializer(
            posts,
            many=True,
            context={"request": request, "starred_post_ids": starred_post_ids},
        )
        return Response(
            {
                "posts": serializer.data,
                "meta": {
                    "count": len(serializer.data),
                    "limit": limit,
                    "filters": {
                        "query": query or None,
                        "tag": tag or None,
                        "starred": True if starred_only else None,
                    },
                },
            }
        )

    def post(self, request):
        if not request.user or not request.user.is_authenticated:
            return error_response("AUTHENTICATION_REQUIRED", status.HTTP_403_FORBIDDEN)

        serializer = CommunityPostWriteSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return error_response("INVALID_COMMUNITY_POST", status.HTTP_400_BAD_REQUEST, serializer.errors)

        post = serializer.save()
        response_serializer = CommunityPostSerializer(post, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class CommunityPostDetailAPIView(APIView):
    permission_classes = [AllowAny]

    def _get_post(self, post_id):
        return CommunityPost.objects.select_related("author").filter(id=post_id).first()

    def get(self, request, post_id):
        post = self._get_post(post_id)
        if post is None:
            return error_response("COMMUNITY_POST_NOT_FOUND", status.HTTP_404_NOT_FOUND)
        serializer = CommunityPostSerializer(post, context={"request": request})
        return Response(serializer.data)

    def patch(self, request, post_id):
        post = self._get_post(post_id)
        if post is None:
            return error_response("COMMUNITY_POST_NOT_FOUND", status.HTTP_404_NOT_FOUND)
        if not request.user or not request.user.is_authenticated:
            return error_response("AUTHENTICATION_REQUIRED", status.HTTP_403_FORBIDDEN)
        if post.author_id != request.user.id:
            return error_response("COMMUNITY_POST_FORBIDDEN", status.HTTP_403_FORBIDDEN)

        serializer = CommunityPostWriteSerializer(
            post,
            data=request.data,
            partial=True,
            context={"request": request, "partial": True},
        )
        if not serializer.is_valid():
            return error_response("INVALID_COMMUNITY_POST", status.HTTP_400_BAD_REQUEST, serializer.errors)

        post = serializer.save()
        response_serializer = CommunityPostSerializer(post, context={"request": request})
        return Response(response_serializer.data)

    def delete(self, request, post_id):
        post = self._get_post(post_id)
        if post is None:
            return error_response("COMMUNITY_POST_NOT_FOUND", status.HTTP_404_NOT_FOUND)
        if not request.user or not request.user.is_authenticated:
            return error_response("AUTHENTICATION_REQUIRED", status.HTTP_403_FORBIDDEN)
        if post.author_id != request.user.id:
            return error_response("COMMUNITY_POST_FORBIDDEN", status.HTTP_403_FORBIDDEN)

        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CommunityPostStarAPIView(APIView):
    permission_classes = [AllowAny]

    def _get_post(self, post_id):
        return CommunityPost.objects.select_related("author").filter(id=post_id).first()

    def post(self, request, post_id):
        if not request.user or not request.user.is_authenticated:
            return error_response("AUTHENTICATION_REQUIRED", status.HTTP_403_FORBIDDEN)

        post = self._get_post(post_id)
        if post is None:
            return error_response("COMMUNITY_POST_NOT_FOUND", status.HTTP_404_NOT_FOUND)

        _, created = CommunityPostBookmark.objects.get_or_create(user=request.user, post=post)
        serializer = CommunityPostSerializer(
            post,
            context={"request": request, "starred_post_ids": {post.id}},
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def delete(self, request, post_id):
        if not request.user or not request.user.is_authenticated:
            return error_response("AUTHENTICATION_REQUIRED", status.HTTP_403_FORBIDDEN)

        post = self._get_post(post_id)
        if post is None:
            return error_response("COMMUNITY_POST_NOT_FOUND", status.HTTP_404_NOT_FOUND)

        CommunityPostBookmark.objects.filter(user=request.user, post=post).delete()
        serializer = CommunityPostSerializer(
            post,
            context={"request": request, "starred_post_ids": set()},
        )
        return Response(serializer.data)
