from typing import Required
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    pass


class Content(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    percentage_of_illegality = models.BigIntegerField(default = -1, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "pending"),
            ("approved", "approved"),
            ("rejected", "rejected"),
        ],
        default="pending",
    )

    class Meta:
        abstract = True


class Text(Content):
    author = models.ForeignKey(User, related_name="texts", on_delete=models.CASCADE)
    text_string = models.TextField()


class Image(Content):
    author = models.ForeignKey(User, related_name="images", on_delete=models.CASCADE)
    image_file = models.ImageField(upload_to="images/")
    is_loaded_in_AWS = models.BooleanField(default=False)


class Video(Content):
    author = models.ForeignKey(User, related_name="videos", on_delete=models.CASCADE)
    video_file = models.FileField(upload_to="videos/")
    is_loaded_in_AWS = models.BooleanField(default=False)

