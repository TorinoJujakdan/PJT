from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import VehicleProfile
from .serializers import VehicleProfileSerializer


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
        
        existing_count = VehicleProfile.objects.filter(user=request.user).count()
        is_default = True if existing_count == 0 else request.data.get("is_default", False)
        
        if is_default:
            VehicleProfile.objects.filter(user=request.user).update(is_default=False)
            
        profile = serializer.save(user=request.user, is_default=is_default)
        return Response({"vehicle": VehicleProfileSerializer(profile).data}, status=status.HTTP_201_CREATED)


class MyVehicleProfileDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        profile = get_object_or_404(VehicleProfile, user=request.user, pk=pk)
        serializer = VehicleProfileSerializer(profile, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response("INVALID_VEHICLE_PROFILE", status.HTTP_400_BAD_REQUEST, serializer.errors)

        is_default = serializer.validated_data.get("is_default")
        if is_default:
            VehicleProfile.objects.filter(user=request.user).exclude(pk=pk).update(is_default=False)

        profile = serializer.save()
        return Response({"vehicle": VehicleProfileSerializer(profile).data})

    def put(self, request, pk):
        profile = get_object_or_404(VehicleProfile, user=request.user, pk=pk)
        serializer = VehicleProfileSerializer(profile, data=request.data)
        if not serializer.is_valid():
            return error_response("INVALID_VEHICLE_PROFILE", status.HTTP_400_BAD_REQUEST, serializer.errors)

        is_default = serializer.validated_data.get("is_default")
        if is_default:
            VehicleProfile.objects.filter(user=request.user).exclude(pk=pk).update(is_default=False)

        profile = serializer.save()
        return Response({"vehicle": VehicleProfileSerializer(profile).data})

    def delete(self, request, pk):
        profile = get_object_or_404(VehicleProfile, user=request.user, pk=pk)
        was_default = profile.is_default
        profile.delete()
        
        if was_default:
            next_profile = VehicleProfile.objects.filter(user=request.user).first()
            if next_profile:
                next_profile.is_default = True
                next_profile.save()
                
        return Response(status=status.HTTP_204_NO_CONTENT)


class SetDefaultVehicleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        profile = get_object_or_404(VehicleProfile, user=request.user, pk=pk)
        
        VehicleProfile.objects.filter(user=request.user).update(is_default=False)
        profile.is_default = True
        profile.save()
        
        return Response({"vehicle": VehicleProfileSerializer(profile).data})
