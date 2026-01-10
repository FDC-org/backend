import datetime

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import UserDetails, InscanModel, BookingDetails


class Inscan(APIView):
    def get(self, r, date):
        if not date:
            return Response(
                {"error": "not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        inscandata = InscanModel.objects.filter(
            inscaned_branch_code=UserDetails.objects.get(user=r.user).code,
            date__date=date,
        )
        data = []
        for i in inscandata:
            try:
                bookingdata = BookingDetails.objects.filter(awbno=i.awbno)
                pcs = bookingdata[0].pcs
                wt = bookingdata[0].wt
                doc_type = bookingdata[0].doc_type
            except Exception as e:
                pcs = ""
                wt = ""
                doc_type = ""
            data.append(
                {
                    "awbno": i.awbno,
                    "date": i.date,
                    "type": doc_type,
                    "pcs": pcs,
                    "wt": wt,
                }
            )
        return Response({"status": "success", "data": data})

    def post(self, r):
        awb_no = r.data["awbno"]
        branch_code = UserDetails.objects.get(user=r.user)
        try:
            for i in awb_no:
                dt_naive = datetime.datetime.strptime(i[0], "%d-%m-%Y, %H:%M:%S")
                InscanModel.objects.create(
                    awbno=i[1], inscaned_branch_code=branch_code.code, date=dt_naive
                )
            return Response({"status": "success"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            print(e)
            return Response({"status": "error"}, status=status.HTTP_406_NOT_ACCEPTABLE)


class InscanMobile(APIView):
    def get(self, r, date):
        if not date:
            return Response(
                {"error": "not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        inscandata = InscanModel.objects.filter(
            inscaned_branch_code=UserDetails.objects.get(user=r.user).code,
            date__date=date,
        )
        data = []
        for i in inscandata:
            try:
                bookingdata = BookingDetails.objects.filter(awbno=i.awbno)
                pcs = bookingdata[0].pcs
                wt = bookingdata[0].wt
                doc_type = bookingdata[0].doc_type
            except Exception as e:
                pcs = ""
                wt = ""
                doc_type = ""
            data.append(
                {
                    "awbno": i.awbno,
                    "date": i.date,
                    "type": doc_type,
                    "pcs": pcs,
                    "wt": wt,
                }
            )
        return Response({"status": "success", "data": data})

    def post(self, r):
        awb_no = r.data["awbno"]
        branch_code = UserDetails.objects.get(user=r.user)
        date = r.data["date"]
        dt_naive = datetime.datetime.strptime(date, "%d-%m-%Y, %H:%M:%S")
        try:
            for i in awb_no:
                InscanModel.objects.create(
                    awbno=i, inscaned_branch_code=branch_code.code, date=dt_naive
                )
            return Response({"status": "success"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            print(e)
            return Response({"status": "error"}, status=status.HTTP_406_NOT_ACCEPTABLE)
