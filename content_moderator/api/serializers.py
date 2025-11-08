from rest_framework import serializers

from ..models import Image, Text, User, Video
from content_moderator.services.AwsService import generatePresignedURL




class ContentSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source="author.username")


class TextSerializer(ContentSerializer):
    class Meta:
        model = Text
        fields = "__all__"


class ImageSerializer(ContentSerializer):
    class Meta:
        model = Image
        fields = "__all__"

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if self.is_loaded_in_AWS:
            rep["image_file"] = generatePresignedURL(instance.image_file.name)
        else:
            rep["image_file"] = generateServerURL(instance.image_file.name)
        return rep


class VideoSerializer(ContentSerializer):
    class Meta:
        model = Video
        fields = "__all__"
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["video_file"] = generatePresignedURL(instance.video_file.name)
        return rep


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "password"]

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"], password=validated_data["password"]
        )
