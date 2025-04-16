from django.http import JsonResponse
from rest_framework.response import Response

from . import models


class CustomMiddleware:
    def __init__(self, get_reponse):
        self.get_response = get_reponse

    def __call__(self, request, *args, **kwargs):
        request.user = None
        auth_header = request.headers.get('Authorization')

        if request.path.startswith('/admin/') or request.path.startswith('/api/login/'):
            return None

        if not auth_header or not auth_header.startswith("Token "):
            return JsonResponse({'error': 'token needed'}, status=401)

        if auth_header and auth_header.startswith('Token '):
            token = auth_header.split(' ')[1]

            try:
                token = models.CustomTokenModel.objects.get(token=token)
                if token.is_expired():
                    token.delete()
                    return JsonResponse({'error': "token expired"}, status=401)
                request.user = token.user

            except models.CustomTokenModel.DoesNotExist:
                return JsonResponse({'error': "invalid token"}, status=401)

        return self.get_response
