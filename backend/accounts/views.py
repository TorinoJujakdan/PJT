from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import AnonRateThrottle

from .serializers import LoginSerializer, SignupSerializer, UserSerializer


ERROR_MESSAGES = {
    "INVALID_SIGNUP": "회원가입 입력값이 올바르지 않습니다.",
    "INVALID_LOGIN": "아이디 또는 비밀번호가 올바르지 않습니다.",
    "AUTHENTICATION_REQUIRED": "로그인이 필요합니다.",
    "INVALID_PROFILE": "회원정보 입력값이 올바르지 않습니다.",
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


class SignupAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("INVALID_SIGNUP", status.HTTP_400_BAD_REQUEST, serializer.errors)
        user = serializer.save()
        login(request, user)
        return Response({"user": UserSerializer(user).data}, status=status.HTTP_201_CREATED)


class LoginAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("INVALID_LOGIN", status.HTTP_400_BAD_REQUEST, serializer.errors)

        user = authenticate(
            request=request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            return error_response("INVALID_LOGIN", status.HTTP_400_BAD_REQUEST)

        login(request, user)
        return Response({"user": UserSerializer(user).data})


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class MeAPIView(APIView):
    def get_permissions(self):
        return [AllowAny()]

    def get(self, request):
        if not request.user or not request.user.is_authenticated:
            return Response({"authenticated": False, "user": None})
        return Response({"authenticated": True, "user": UserSerializer(request.user).data})

    def patch(self, request):
        if not request.user or not request.user.is_authenticated:
            return error_response("AUTHENTICATION_REQUIRED", status.HTTP_403_FORBIDDEN)

        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response("INVALID_PROFILE", status.HTTP_400_BAD_REQUEST, serializer.errors)
        serializer.save()
        return Response({"user": serializer.data})
