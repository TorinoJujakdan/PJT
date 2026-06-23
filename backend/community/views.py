from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CommunityPost
from .serializers import CommunityPostSerializer, CommunityPostWriteSerializer


DEFAULT_LIST_LIMIT = 50
MAX_LIST_LIMIT = 100

ERROR_MESSAGES = {
    "AUTHENTICATION_REQUIRED": "Authentication is required.",
    "COMMUNITY_POST_NOT_FOUND": "Community post was not found.",
    "COMMUNITY_POST_FORBIDDEN": "Only the author can modify this community post.",
    "INVALID_COMMUNITY_POST": "Community post input is invalid.",
    "STATION_NOT_FOUND": "Gas station was not found.",
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


def _has_station_not_found_error(serializer):
    station_errors = serializer.errors.get("station_id") if isinstance(serializer.errors, dict) else None
    if not station_errors:
        return False
    return any(str(error) == "STATION_NOT_FOUND" for error in station_errors)


def _post_has_exact_tag(post, tag):
    normalized_tag = tag.casefold()
    return any(isinstance(item, str) and item.casefold() == normalized_tag for item in post.tags)


class CommunityPostListCreateAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        queryset = CommunityPost.objects.select_related("station", "author").all()
        station_id = (request.query_params.get("station_id") or "").strip()
        query = (request.query_params.get("query") or "").strip()
        tag = (request.query_params.get("tag") or "").strip()
        limit = _parse_limit(request.query_params.get("limit"))

        if station_id:
            try:
                queryset = queryset.filter(station_id=int(station_id))
            except ValueError:
                return error_response(
                    "INVALID_COMMUNITY_POST",
                    status.HTTP_400_BAD_REQUEST,
                    {"station_id": ["station_id must be an integer."]},
                )
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(content__icontains=query)
                | Q(station__name__icontains=query)
                | Q(station__address__icontains=query)
            )
        if tag:
            posts = []
            for post in queryset.iterator():
                if _post_has_exact_tag(post, tag):
                    posts.append(post)
                if len(posts) >= limit:
                    break
        else:
            posts = list(queryset[:limit])
        serializer = CommunityPostSerializer(posts, many=True, context={"request": request})
        return Response(
            {
                "posts": serializer.data,
                "meta": {
                    "count": len(serializer.data),
                    "limit": limit,
                    "filters": {
                        "station_id": station_id or None,
                        "query": query or None,
                        "tag": tag or None,
                    },
                },
            }
        )

    def post(self, request):
        if not request.user or not request.user.is_authenticated:
            return error_response("AUTHENTICATION_REQUIRED", status.HTTP_403_FORBIDDEN)

        serializer = CommunityPostWriteSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            if _has_station_not_found_error(serializer):
                return error_response("STATION_NOT_FOUND", status.HTTP_404_NOT_FOUND, serializer.errors)
            return error_response("INVALID_COMMUNITY_POST", status.HTTP_400_BAD_REQUEST, serializer.errors)

        post = serializer.save()
        response_serializer = CommunityPostSerializer(post, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class CommunityPostDetailAPIView(APIView):
    permission_classes = [AllowAny]

    def _get_post(self, post_id):
        return CommunityPost.objects.select_related("station", "author").filter(id=post_id).first()

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
            if _has_station_not_found_error(serializer):
                return error_response("STATION_NOT_FOUND", status.HTTP_404_NOT_FOUND, serializer.errors)
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
