import datetime

from django.dispatch import receiver
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import UserDetails, DrsDetails, DRS, DeliveryBoyDetalis, DeliveryDetails, deliverdordrs

class DRS(APIView):
    def get(self, r,date):
        if not date:
            return Response({'status': 'not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        drsdetails = DRS.objects.filter(date__date=date,branch = UserDetails.objects.get(user=r.user).code)
        data = []
        for i in drsdetails:
            s = "ofd"
            awbdata = []
            for awbno in DrsDetails.objects.filter(drsno=i.drsno).all():
                if awbno.status:
                    d = DeliveryDetails.objects.filter(awbno=awbno.awbno)
                    if d.exists():
                        s = d[0].status
                awbdata.append({"awbno":awbno.awbno,"status":s})
            data.append({"date": i.date,"drsno":i.drsno,"boy":DeliveryBoyDetalis.objects.get(name=i.boy_code).name,
                             "location":i.location,"awbdata":awbdata})
        return Response({"status":"success","data":data},status=status.HTTP_200_OK)


    def post(self, r):
        awbno = r.data['awbno']
        delivery_boy = r.data['delivery_boy']
        date = r.data['date']
        lcoation = r.data['location']
        branch = UserDetails.objects.get(user=r.user)
        dt_naive = datetime.datetime.strptime(date, "%d-%m-%Y, %H:%M:%S")
        try:
            for no in awbno:
                if deliverdordrs.objects.filter(awbno=no).exists():
                        return Response({"status":"exists","awbno":no},status=status.HTTP_409_CONFLICT)
            for no in awbno:
                DrsDetails.objects.create(drsno = branch.drs_number, awbno = no)
                deliverdordrs.objects.create(awbno = no)
            DRS.objects.create(data =dt_naive,boy_code = DeliveryBoyDetalis.objects.get(name=delivery_boy),
                               branch = branch,drsno=branch.drs_number,location=lcoation)
            branch.drs_number = str(int(branch.drs_number) + 1)
            branch.save()
            return Response({"status": "success"},status=status.HTTP_201_CREATED)
        except Exception as e:
            print(e)
            da = DRS.objects.filter(drsno=branch.drs_number)
            if da:
                da[0].delete()
            d = DrsDetails.objects.filter(drsno=branch.drs_number)
            if d:
                for i in d:
                    i.delete()
            return Response({"status":"error"},status=status.HTTP_400_BAD_REQUEST)

class Delivered(APIView):
    def get(self, r):
        return Response({"status":"method not allowed"},status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def post(self, r):
        awbno = r.data['awbno']
        awbstatus = r.data['status'].strip().lower()
        try:
            if awbstatus == 'delivered':
                receivername = r.data['receivername']
                image = r.FILES.get('image')
                for awb in awbno:
                    DeliveryDetails.objects.create(awbno = awb,status = 'delivered',receivername = receivername,image = image)
            elif awbstatus == 'undelivered' or  awbstatus == 'rto':
                reason = r.data['reason']
                statusre = "undelivered" if awbstatus == 'undelivered' else "rto"
                for awb in awbno:
                    deliverdordrs.objects.filter(awbno=awb).delete()
                    DeliveryDetails.objects.create(awbno=awb, status=statusre, reason=reason)
            else:
                return Response({"status":"invalid status"}, status=awbstatus.HTTP_400_BAD_REQUEST)
            return Response({"status":"success",}, status=status.HTTP_201_CREATED)
        except Exception as e:
            print(e)
            return Response({"status":"error"},status=status.HTTP_400_BAD_REQUEST)

