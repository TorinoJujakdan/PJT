from rest_framework import serializers

from stations.models import GasStation

from .models import CommunityPost


MAX_CONTENT_LENGTH = 2000
MAX_TAGS = 10
MAX_TAG_LENGTH = 20


class CommunityPostSerializer(serializers.ModelSerializer):
    station = serializers.SerializerMethodField()
    author = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = CommunityPost
        fields = [
            "id",
            "station",
            "author",
            "title",
            "content",
            "tags",
            "created_at",
            "updated_at",
            "can_edit",
        ]

    def get_station(self, obj):
        return {
            "station_id": obj.station_id,
            "name": obj.station.name,
            "brand": obj.station.brand,
            "address": obj.station.address,
        }

    def get_author(self, obj):
        return {
            "id": obj.author_id,
            "username": obj.author.get_username(),
        }

    def get_can_edit(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and user.id == obj.author_id)


class CommunityPostWriteSerializer(serializers.Serializer):
    station_id = serializers.IntegerField(required=False)
    title = serializers.CharField(max_length=120, required=False)
    content = serializers.CharField(required=False)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=MAX_TAG_LENGTH),
        required=False,
        allow_empty=True,
    )

    def validate_title(self, value):
        title = value.strip()
        if not title:
            raise serializers.ValidationError("title must not be blank.")
        return title

    def validate_content(self, value):
        content = value.strip()
        if not content:
            raise serializers.ValidationError("content must not be blank.")
        if len(content) > MAX_CONTENT_LENGTH:
            raise serializers.ValidationError(f"content must be at most {MAX_CONTENT_LENGTH} characters.")
        return content

    def validate_tags(self, value):
        cleaned_tags = []
        seen = set()
        for raw_tag in value:
            tag = raw_tag.strip()
            if not tag:
                continue
            key = tag.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned_tags.append(tag)
        if len(cleaned_tags) > MAX_TAGS:
            raise serializers.ValidationError(f"tags must contain at most {MAX_TAGS} items.")
        return cleaned_tags

    def validate_station_id(self, value):
        if not GasStation.objects.filter(id=value).exists():
            raise serializers.ValidationError("STATION_NOT_FOUND")
        return value

    def validate(self, attrs):
        is_partial = self.context.get("partial", False)
        if not is_partial:
            missing_fields = [field for field in ["station_id", "title", "content"] if field not in attrs]
            if missing_fields:
                raise serializers.ValidationError({field: "This field is required." for field in missing_fields})
        if not attrs:
            raise serializers.ValidationError("At least one field must be provided.")
        return attrs

    def create(self, validated_data):
        station_id = validated_data.pop("station_id")
        return CommunityPost.objects.create(
            station_id=station_id,
            author=self.context["request"].user,
            **validated_data,
        )

    def update(self, instance, validated_data):
        station_id = validated_data.pop("station_id", None)
        if station_id is not None:
            instance.station_id = station_id
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save(update_fields=["station", "title", "content", "tags", "updated_at"])
        return instance
