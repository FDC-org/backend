import datetime

from django.utils import timezone


def token_expiry():
    return timezone.now() + datetime.timedelta(days=6)