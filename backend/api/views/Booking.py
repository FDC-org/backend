from rest_framework.response import Response
from rest_framework.views import APIView

from backend.api.models import UserDetails, BookingDetails


class Booking(APIView):
    def get(self,request):
        return Response({"status":"ok"})

    def post(self,request):
        awbno = request.data['awbno']
        date = request.data['date']
        doc_type = request.data['doc_type']
        pcs = request.data['pcs']
        wt = request.data['wt']
        sendername = request.data['sendername']
        receivername = request.data['receivername']
        senderphone = request.data['senderphone']
        receiverphone = request.data['receiverphone']
        senderaddress = request.data['senderaddress']
        receiveraddress = request.data['receiveraddress']
        destination_code = request.data['destination_code']
        mode = request.data['mode']
        booked_code = UserDetails.objects.get(user=request.user)
        contents = request.data['contents']
        pincode = request.data['pincode']
        if BookingDetails.objects.filter(awbno=awbno).exists():
            return Response({"status":"Already Booked"})
        try:
            BookingDetails.objects.create(awbno=awbno,pcs=pcs,wt=wt,sendername=sendername,
                                          receivername=receivername,senderaddress=senderaddress,
                                          receiveraddress=receiveraddress,senderphonenumber=senderphone,
                                          receiverphonenumber=receiverphone,doc_type=doc_type,
                                          destination_code=destination_code,mode=mode,date=date,
                                          booked_code=booked_code,contents=contents,pincode=pincode)
            return Response({"status":"success"})
        except Exception as e:
            print("error")
            return Response({"status":"error"})