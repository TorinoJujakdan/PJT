from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import VehicleProfile
from .serializers import VehicleProfileSerializer

User = get_user_model()

ERROR_MESSAGES = {
    "VEHICLE_PROFILE_NOT_FOUND": "저장된 차량 프로필이 없습니다.",
    "INVALID_VEHICLE_PROFILE": "차량 프로필 입력값이 올바르지 않습니다.",
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


class MyVehicleProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = VehicleProfile.objects.filter(user=request.user, is_default=True).first()
        if profile is None:
            return error_response("VEHICLE_PROFILE_NOT_FOUND", status.HTTP_404_NOT_FOUND)
        return Response({"vehicle": VehicleProfileSerializer(profile).data})

    def put(self, request):
        profile = VehicleProfile.objects.filter(user=request.user, is_default=True).first()
        serializer = VehicleProfileSerializer(instance=profile, data=request.data)
        if not serializer.is_valid():
            return error_response("INVALID_VEHICLE_PROFILE", status.HTTP_400_BAD_REQUEST, serializer.errors)
        profile = serializer.save(user=request.user, is_default=True)
        return Response({"vehicle": VehicleProfileSerializer(profile).data})


class MyVehicleProfilesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profiles = VehicleProfile.objects.filter(user=request.user)
        return Response({"vehicles": VehicleProfileSerializer(profiles, many=True).data})

    def post(self, request):
        serializer = VehicleProfileSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("INVALID_VEHICLE_PROFILE", status.HTTP_400_BAD_REQUEST, serializer.errors)

        with transaction.atomic():
            User.objects.select_for_update().get(pk=request.user.pk)
            is_default = not VehicleProfile.objects.filter(user=request.user).exists()
            profile = serializer.save(user=request.user, is_default=is_default)
        return Response({"vehicle": VehicleProfileSerializer(profile).data}, status=status.HTTP_201_CREATED)


class MyVehicleProfileDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        profile = get_object_or_404(VehicleProfile, user=request.user, pk=pk)
        serializer = VehicleProfileSerializer(profile, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response("INVALID_VEHICLE_PROFILE", status.HTTP_400_BAD_REQUEST, serializer.errors)

        profile = serializer.save()
        return Response({"vehicle": VehicleProfileSerializer(profile).data})

    def put(self, request, pk):
        profile = get_object_or_404(VehicleProfile, user=request.user, pk=pk)
        serializer = VehicleProfileSerializer(profile, data=request.data)
        if not serializer.is_valid():
            return error_response("INVALID_VEHICLE_PROFILE", status.HTTP_400_BAD_REQUEST, serializer.errors)

        profile = serializer.save()
        return Response({"vehicle": VehicleProfileSerializer(profile).data})

    def delete(self, request, pk):
        with transaction.atomic():
            User.objects.select_for_update().get(pk=request.user.pk)
            profile = get_object_or_404(
                VehicleProfile.objects.select_for_update(),
                user=request.user,
                pk=pk,
            )
            was_default = profile.is_default
            profile.delete()

            if was_default:
                next_profile = VehicleProfile.objects.filter(user=request.user).first()
                if next_profile:
                    next_profile.is_default = True
                    next_profile.save(update_fields=["is_default", "updated_at"])
                
        return Response(status=status.HTTP_204_NO_CONTENT)


class SetDefaultVehicleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        with transaction.atomic():
            User.objects.select_for_update().get(pk=request.user.pk)
            profile = get_object_or_404(
                VehicleProfile.objects.select_for_update(),
                user=request.user,
                pk=pk,
            )
            VehicleProfile.objects.filter(user=request.user, is_default=True).exclude(pk=pk).update(is_default=False)
            if not profile.is_default:
                profile.is_default = True
                profile.save(update_fields=["is_default", "updated_at"])
        
        return Response({"vehicle": VehicleProfileSerializer(profile).data})
