import datetime
import time
import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


# Create your models here.

class CustomTokenModel(models.Model):
    token = models.CharField(default=uuid.UUID, max_length=100)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='custom_token')
    created_at = models.DateTimeField(auto_now_add=True)
    expired_at = models.DurationField(default=datetime.timedelta(days=5))

    def __str__(self):
        return self.user

    def is_expired(self):
        return timezone.now() >= self.created_at + self.expired_at


class UserDetails(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='users')
    type = models.CharField(max_length=10)
    branch_name = models.CharField(max_length=50)
    location = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    address = models.CharField(max_length=200)
