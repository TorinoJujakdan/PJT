from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Card

User = get_user_model()

class CardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Card
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    cards = CardSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'car_efficiency', 'cards']

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'car_efficiency']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            car_efficiency=validated_data.get('car_efficiency', 10.0)
        )
        return user
