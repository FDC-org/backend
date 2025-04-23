from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class Dashboard(APIView):
    def get(self, r):
        try:
            if r.new_token:
                return Response({'data': "Hello" + str(r.user), 'new_token': r.new_token})
        except:
            return Response({'data': "Hello" + str(r.user)})
