from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import UserDetails, BookingDetails_temp


class UseDetails(APIView):
    def get(self, r):
        user = r.user
        userdetails = UserDetails.objects.get(user=user)
        try:
            if r.new_token:
                return Response({'new_token':r.new_token,'type': userdetails.type, 'name': userdetails.fullname(), 'code_name': userdetails.code_name})
        except:
            return Response({'new_token':'none','type': userdetails.type, 'name': userdetails.fullname(), 'code_name': userdetails.code_name})


class GetBookingDetails(APIView):
    def post(self, r):
        details = BookingDetails_temp.objects.filter(awbno=r.data['awbno'])
        if details:
            return Response(
                {"status": "found", 'type': details[0].doc_type, 'pcs': details[0].pcs, 'wt': details[0].wt})
        else:
            return Response({'status': 'not found'})


class AddBookingDetails(APIView):
    def post(self, r):
        BookingDetails_temp.objects.create(awbno=r.data['awbno'], doc_type=r.data['doctype'],
                                                     pcs=r.data['pcs'], wt=r.data['wt'])
        return Response({'status': "added"})
