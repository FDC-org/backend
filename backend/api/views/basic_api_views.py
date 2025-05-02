from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import UserDetails, BookingDetails_temp, HubDetails, Vehicle_Details


class UseDetails(APIView):
    def get(self, r):
        user = r.user
        userdetails = UserDetails.objects.get(user=user)
        try:
            if r.new_token:
                return Response({'new_token': r.new_token, 'type': userdetails.type, 'name': userdetails.fullname(),
                                 'code_name': userdetails.code_name})
        except:
            return Response({'new_token': 'none', 'type': userdetails.type, 'name': userdetails.fullname(),
                             'code_name': userdetails.code_name})


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


class GetManifestNumber(APIView):
    def get(self, r):
        return Response({"manifestno": UserDetails.objects.get(user=r.user).manifestnumber})


class GetHubList(APIView):
    def get(self, r):
        hubs = []
        data = HubDetails.objects.all()
        for i in data:
            if i.hub_code != UserDetails.objects.get(user=r.user).code:
                hubs.append({"code": i.hub_code, "name": i.hubname})
        return Response({"hub": hubs})


class VehicleDetails(APIView):
    def get(self, r):
        data = []
        for i in Vehicle_Details.objects.filter(hub_code=UserDetails.objects.get(user=r.user).code):
            data.append(i.vehiclenumber)
        return Response({"data": data})

    def post(self, r):
        vehicle_number = r.data['vehicle_number']
        try:
            Vehicle_Details.objects.create(hub_code=UserDetails.objects.get(user=r.user).code, vehiclenumber=vehicle_number)
            return Response({"status": "added"})
        except Exception as e:
            print(e)
            return Response({"status": "error"})


