import datetime

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import (
    UserDetails,
    OutscanModel,
    ManifestDetails,
    Vehicle_Details,
    BookingDetails, HubDetails, BranchDetails,
)


class OutScan(APIView):
    def get(self, r, date):
        if not date:
            return Response(
                {"error": "not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        manifesstdata = ManifestDetails.objects.filter(
            inscaned_branch_code=UserDetails.objects.get(user=r.user).code,
            date__date=date,
        )
        data = []
        for i in manifesstdata:
            vehicle_num = ""
            if i.vehicle_number:
                vehicle_num = i.vehicle_number.vehiclenumber
            data.append(
                {
                    "date": i.date,
                    "manifestnumber": i.manifestnumber,
                    "tohub": UserDetails.objects.get(
                        code=i.tohub_branch_code
                    ).code_name,
                    "vehicle_number": vehicle_num,
                }
            )
        return Response({"status": "success", "data": data})

    def post(self, r):
        awb_no = r.data["awbno"]
        manifest_number = r.data["manifest_number"]
        vehicle_number = r.data["vehicle_number"]
        tohub = r.data["tohub"]
        branch_code = UserDetails.objects.get(user=r.user)
        date = r.data["date"]
        try:
            dt_naive = datetime.datetime.strptime(date, "%d-%m-%Y, %H:%M:%S")
            manifest = ManifestDetails.objects.create(
                date=dt_naive,
                inscaned_branch_code=branch_code.code,
                tohub_branch_code=UserDetails.objects.get(code_name=tohub).code,
                manifestnumber=manifest_number,
                vehicle_number=Vehicle_Details.objects.get(
                    vehiclenumber=vehicle_number
                ),
            )
            for i in awb_no:
                OutscanModel.objects.create(awbno=i[2], manifestnumber=manifest)
            branch_code.manifestnumber = str(int(branch_code.manifestnumber) + 1)
            branch_code.save()
            return Response(
                {"status": "success", "manifest_number": branch_code.manifestnumber},
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            print(e)
            ma = ManifestDetails.objects.filter(manifestnumber=manifest_number)
            if ma:
                ma[0].delete()
            return Response({"status": "error"}, status=status.HTTP_406_NOT_ACCEPTABLE)


class OutScanMobile(APIView):
    def get(self, r, date):
        if not date:
            return Response(
                {"error": "not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        manifesstdata = ManifestDetails.objects.filter(
            inscaned_branch_code=UserDetails.objects.get(user=r.user).code,
            date__date=date,
        )
        data = []

        for i in manifesstdata:
            vehicle_num = ""
            if i.vehicle_number:
                vehicle_num = i.vehicle_number.vehiclenumber
            data.append(
                {
                    "date": i.date,
                    "manifestnumber": i.manifestnumber,
                    "tohub": UserDetails.objects.get(
                        code=i.tohub_branch_code
                    ).code_name,
                    "vehicle_number": vehicle_num,
                }
            )
        return Response({"status": "success", "data": data})

    def post(self, r):
        awb_no = r.data["awbno"]
        manifest_number = r.data["manifest_number"]
        # vehicle_number = r.data['vehicle_number']
        tohub = r.data["tohub"]
        branch_code = UserDetails.objects.get(user=r.user)
        date = r.data["date"]
        try:
            dt_naive = datetime.datetime.strptime(date, "%d-%m-%Y, %H:%M:%S")
            tohubde = HubDetails.objects.filter(hubname=tohub)
            if tohubde.exists():
                tohub = tohubde[0].hubname
            tobranchde = BranchDetails.objects.filter(branchname=tohubde)
            if tobranchde.exists():
                tohub = tobranchde[0].branch_code
            manifest = ManifestDetails.objects.create(
                date=dt_naive,
                inscaned_branch_code=branch_code.code,
                tohub_branch_code=UserDetails.objects.get(code_name=tohub),
                manifestnumber=manifest_number,
            )
            for i in awb_no:
                OutscanModel.objects.create(awbno=i, manifestnumber=manifest)
            branch_code.manifestnumber = str(int(branch_code.manifestnumber) + 1)
            branch_code.save()
            return Response(
                {"status": "success", "manifest_number": branch_code.manifestnumber},
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            print(e)
            ma = ManifestDetails.objects.filter(manifestnumber=manifest_number)
            if ma:
                ma[0].delete()
            oa = OutscanModel.objects.filter(manifestnumber=manifest_number)
            if oa:
                for i in oa:
                    i.delete()
            return Response({"status": "error"}, status=status.HTTP_406_NOT_ACCEPTABLE)


class ManifestData(APIView):
    def get(self, r, manifest_number):
        if not manifest_number:
            return Response(
                {"error": "not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED
            )

        data = []
        manifest_details = ManifestDetails.objects.get(manifestnumber=manifest_number)
        vehicle_num = (
            manifest_details.vehicle_number.vehiclenumber
            if manifest_details.vehicle_number
            else ""
        )
        for i in OutscanModel.objects.filter(
            manifestnumber=ManifestDetails.objects.get(manifestnumber=manifest_number)
        ):
            awbdetails = BookingDetails.objects.filter(awbno=i.awbno)
            pcs = ""
            wt = ""
            if awbdetails:
                pcs = awbdetails[0].pcs
                wt = awbdetails[0].wt
            data.append({"awbno": i.awbno, "pcs": pcs, "wt": wt})
        return Response(
            {
                "status": "success",
                "date": manifest_details.date,
                "tohub": UserDetails.objects.get(
                    code=manifest_details.tohub_branch_code
                ).code_name,
                "vehicle_number": vehicle_num,
                "awbno": data,
            }
        )
