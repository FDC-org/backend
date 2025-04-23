from django.contrib.auth import authenticate
from django.http import JsonResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from ..models import CustomTokenModel
from django.views.decorators.csrf import ensure_csrf_cookie


class Login(APIView):
    def get(self, r):
        return Response({'error': 'get method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def post(self, r):
        username = r.data['username']
        password = r.data['password']
        user = authenticate(username=username, password=password)
        if user:
            token, _ = CustomTokenModel.objects.get_or_create(user=user)
            return Response({'token': token.token}, status=status.HTTP_202_ACCEPTED)

        else:
            return Response({'error': 'invalid username or password'}, status=status.HTTP_401_UNAUTHORIZED)


@ensure_csrf_cookie
def csrf_token(r):
    return JsonResponse({'status': "csrf set"})
