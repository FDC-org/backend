import json
from datetime import timedelta

from django.http import JsonResponse
from django.utils import timezone
from rest_framework.response import Response

from . import models


class CustomMiddleware:
    def __init__(self, get_reponse):
        self.get_response = get_reponse

    def __call__(self, request, *args, **kwargs):
        request.user = None
        auth_header = request.headers.get('Authorization')

        if request.path.startswith('/admin/') or request.path.startswith('/api/login/'):
            return self.get_response(request)

        if not auth_header or not auth_header.startswith("Token "):
            return JsonResponse({'error': 'token needed'}, status=401)

        token = auth_header.split(' ')[1]

        try:
            token = models.CustomTokenModel.objects.get(token=token)
            if token.is_expired():
                token.delete()
                return JsonResponse({'error': "token expired"}, status=401)
            request.user = token.user

            if token.expired_at - timezone.now() < timedelta(minutes=10):
                token.delete()
                request.new_token = models.CustomTokenModel.objects.create(user=token.user).token

        except models.CustomTokenModel.DoesNotExist:
            return JsonResponse({'error': "invalid token"})

        return self.get_response(request)
