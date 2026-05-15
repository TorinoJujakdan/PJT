from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from .serializers import UserSerializer, UserCreateSerializer, CardSerializer
from .models import Card

class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            return Response({'token': token.key, 'user': UserSerializer(user).data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({'token': token.key, 'user': UserSerializer(user).data}, status=status.HTTP_200_OK)
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

class ProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        user = request.user
        car_efficiency = request.data.get('car_efficiency')
        if car_efficiency is not None:
            user.car_efficiency = car_efficiency
            user.save()
            return Response(UserSerializer(user).data, status=status.HTTP_200_OK)
        return Response({'error': 'car_efficiency field required'}, status=status.HTTP_400_BAD_REQUEST)

class CardListAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cards = Card.objects.all()
        serializer = CardSerializer(cards, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CardSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserCardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, card_id):
        try:
            card = Card.objects.get(id=card_id)
            request.user.cards.add(card)
            return Response({'message': f'Card {card.card_name} added to your profile.'}, status=status.HTTP_200_OK)
        except Card.DoesNotExist:
            return Response({'error': 'Card not found'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, card_id):
        try:
            card = Card.objects.get(id=card_id)
            request.user.cards.remove(card)
            return Response({'message': f'Card {card.card_name} removed from your profile.'}, status=status.HTTP_200_OK)
        except Card.DoesNotExist:
            return Response({'error': 'Card not found'}, status=status.HTTP_404_NOT_FOUND)
