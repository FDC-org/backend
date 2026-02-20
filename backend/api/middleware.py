# from datetime import timedelta
#
# from django.http import JsonResponse
# from django.utils import timezone
#
# from . import models
#
#
# class CustomMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response
#
#     def __call__(self, request):
#
#         # ✅ Admin & browser routes untouched
#         if (
#             request.path.startswith('/admin/')
#             or request.path.startswith('/static/')
#             or request.path.startswith('/media/')
#             or request.path == '/favicon.ico'
#         ):
#             return self.get_response(request)
#
#         # ✅ Non-API routes untouched
#         if not request.path.startswith('/api/'):
#             return self.get_response(request)
#
#         # ✅ Allow OPTIONS
#         if request.method == "OPTIONS":
#             return self.get_response(request)
#
#         # 🔐 API token auth only
#         auth_header = request.headers.get('Authorization')
#
#         if not auth_header or not auth_header.startswith("Token "):
#             return JsonResponse({'error': 'token needed'}, status=401)
#
#         token_value = auth_header.split(' ')[1]
#
#         try:
#             token_obj = models.CustomTokenModel.objects.get(token=token_value)
#
#             if token_obj.is_expired():
#                 token_obj.delete()
#                 return JsonResponse({'error': 'token expired'}, status=401)
#
#             request.user = token_obj.user
#             if token_obj.expired_at - timezone.now() < timedelta(minutes=10):
#                 token_obj.delete()
#                 request.new_token = models.CustomTokenModel.objects.create(user=token_obj.user).token
#
#
#         except models.CustomTokenModel.DoesNotExist:
#             return JsonResponse({'error': 'invalid token'}, status=401)
#
#         return self.get_response(request)
##   for admin panel use above


from datetime import timedelta

from django.http import JsonResponse
from django.utils import timezone

from . import models


class CustomMiddleware:
    def __init__(self, get_reponse):
        self.get_response = get_reponse

    def __call__(self, request, *args, **kwargs):
        request.user = None
        auth_header = request.headers.get('Authorization')
        setattr(request, '_dont_enforce_csrf_checks', True)

        if request.method == "OPTIONS":
            return self.get_response(request)

        # Allow public access to PDF download/view endpoints and other public routes
        if (request.path.startswith('/api/track/') or 
            request.path.startswith('/api/login/') or 
            request.path.startswith('/api/test/') or 
            request.path.startswith('/api/logout/') or 
            request.path.startswith('/api/drs/download/') or 
            request.path.startswith('/api/drs/view/') or 
            request.path.startswith('/api/manifest/download/') or 
            request.path.startswith('/api/manifest/view/') or 
            request.path.startswith('/admin/')):
            return self.get_response(request)

        if not auth_header or not auth_header.startswith("Token "):
            return JsonResponse({'error': 'token needed'}, status=401)

        token = auth_header.split(' ')[1]

        try:
            token = models.CustomTokenModel.objects.get(token=token)
            if token.is_expired():
                token.delete()
                return JsonResponse({'error': "token expired"}, status=401)
            request._cached_user  = token.user
            if token.expired_at - timezone.now() < timedelta(days=1):
                token.delete()
                request.new_token = models.CustomTokenModel.objects.create(user=token.user).token

        except Exception as e:
            print(e)
            return JsonResponse({'error': "invalid token"}, status=401)

        return self.get_response(request)