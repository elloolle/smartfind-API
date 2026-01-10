from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    customer_id = models.CharField(max_length=200, null=True, blank=True, unique=True)
    may_have_trial = models.BooleanField(default=True)
