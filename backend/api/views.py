from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


# Create your views here.


class Login(APIView):
    def get(self, r):
        return Response({'error': 'get method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def post(self, r):
        return Response(data={'name': r.user},status=400)
