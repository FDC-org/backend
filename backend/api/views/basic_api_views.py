from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import (
    UserDetails,
    BookingDetails_temp,
    HubDetails,
    Vehicle_Details,
    InscanModel,
    OutscanModel,
    BranchDetails,
    BookingDetails,
    AppRelease,
    DRS,
    DeliveryDetails,
    DrsDetails,
)


class UseDetails(APIView):
    def get(self, r):
        user = r.user
        userdetails = UserDetails.objects.get(user=user)
        try:
            if r.new_token:
                return Response(
                    {
                        "new_token": r.new_token,
                        "type": userdetails.type,
                        "name": userdetails.fullname(),
                        "code_name": userdetails.code_name,
                    }
                )
        except:
            return Response(
                {
                    "new_token": "none",
                    "type": userdetails.type,
                    "name": userdetails.fullname(),
                    "code_name": userdetails.code_name,
                }
            )


class GetBookingDetails(APIView):
    def post(self, r):
        details = BookingDetails_temp.objects.filter(awbno=r.data["awbno"])
        if details:
            return Response(
                {
                    "status": "found",
                    "type": details[0].doc_type,
                    "pcs": details[0].pcs,
                    "wt": details[0].wt,
                }
            )
        else:
            return Response({"status": "not found"})


class AddBookingDetails(APIView):
    def post(self, r):
        BookingDetails_temp.objects.create(
            awbno=r.data["awbno"],
            doc_type=r.data["doctype"],
            pcs=r.data["pcs"],
            wt=r.data["wt"],
        )
        return Response({"status": "added"})


class GetManifestNumber(APIView):
    def get(self, r):
        return Response(
            {"manifestno": UserDetails.objects.get(user=r.user).manifestnumber}
        )


class GetHubList(APIView):
    def get(self, r):
        hubs = []
        data = HubDetails.objects.all()
        data2 = BranchDetails.objects.all()
        for i in data:
            if i.hub_code != UserDetails.objects.get(user=r.user).code:
                hubs.append({"code": i.hub_code, "name": i.hubname, "type": "hub"})
        for i in data2:
            if i.branch_code != UserDetails.objects.get(user=r.user).code:
                hubs.append(
                    {"code": i.branch_code, "name": i.branchname, "type": "branch"}
                )
        return Response({"hub": hubs})


class VehicleDetails(APIView):
    def get(self, r):
        data = []
        for i in Vehicle_Details.objects.filter(
            hub_code=UserDetails.objects.get(user=r.user).code
        ):
            data.append(i.vehiclenumber)
        return Response({"data": data})

    def post(self, r):
        vehicle_number = r.data["vehicle_number"]
        try:
            Vehicle_Details.objects.create(
                hub_code=UserDetails.objects.get(user=r.user).code,
                vehiclenumber=vehicle_number,
            )
            return Response({"status": "added"})
        except Exception as e:
            print(e)
            return Response({"status": "error"})


class VerifyToken(APIView):
    def get(self, r):
        try:
            if r.new_token:
                return Response({"new_token": r.new_token, "status": "new_token"})
            return Response({"status": "valid"})
        except:
            return Response({"status": "invalid"})


class Track(APIView):
    def get(self, r, awbno):
        if not awbno:
            return Response({"status": "AWB no required"})
        try:
            tracking_data = []
            inscans = InscanModel.objects.filter(awbno=awbno)
            if inscans:
                for inscan in inscans:
                    tracking_data.append(
                        {
                            "awbno": inscan.awbno,
                            "event": "Inscan",
                            "location": UserDetails.objects.get(
                                code=inscan.inscaned_branch_code
                            ).code_name,
                            "date": inscan.date,
                            "branch_type": UserDetails.objects.get(
                                code=inscan.inscaned_branch_code
                            ).type,
                        }
                    )
            outscans = OutscanModel.objects.filter(awbno=awbno).select_related(
                "manifestnumber__vehicle_number"
            )
            if outscans:
                for outscan in outscans:
                    manifest = outscan.manifestnumber
                    tracking_data.append(
                        {
                            "awbno": outscan.awbno,
                            "event": "Outscan",
                            "location": UserDetails.objects.get(
                                code=manifest.inscaned_branch_code
                            ).code_name,
                            "date": manifest.date,
                            "branch_type": UserDetails.objects.get(
                                code=manifest.inscaned_branch_code
                            ).type,
                            "tohub": UserDetails.objects.get(
                                code=manifest.tohub_branch_code
                            ).code_name,
                        }
                    )

            tracking_data.sort(key=lambda x: x["date"])
            delivery_data = []
            drsdata = []
            drs_details = DrsDetails.objects.filter(awbno=awbno)
            if drs_details.exists():
                drsno = DRS.objects.get(drsno=drs_details[0].drsno)
                drs_date = drsno.date
                drsnum = drsno.drsno
                drsdata.append({"date": drs_date, "drsnum": drsnum})
                deliverydate = ""
                deliveryimage = ""
                deliveryreason = ""
                deliveryrecname = ""
                deliveryrecphone = ""
                if drs_details[0].status:
                    deliverydetails = DeliveryDetails.objects.get(drsno=drsno.drsno)
                    deliverystatus = deliverydetails.status
                    deliverydate = deliverydetails.date
                    deliveryimage = deliverydetails.image
                    deliveryreason = deliverydetails.reason
                    deliveryrecname = deliverydetails.recievername
                    deliveryrecphone = deliverydetails.recievernumber
                else:
                    deliverystatus = "ofd"
                delivery_data.append(
                    {
                        "status": deliverystatus,
                        "deliverydate": deliverydate,
                        "deliveryimage": deliveryimage,
                        deliveryrecname: deliveryrecname,
                        "deliveryrecphone": deliveryrecphone,
                        deliveryreason: deliveryreason,
                    }
                )

            booking_details = BookingDetails.objects.filter(awbno=awbno)
            destination = ""
            if booking_details.exists():
                if HubDetails.objects.filter(
                    booking_details=booking_details[0].destination_code
                ).exists():
                    destination = HubDetails.objects.get(
                        booking_details=booking_details[0].destination_code
                    ).hubname
                elif BranchDetails.objects.filter(
                    booking_details=booking_details[0].destination_code
                ).exists():
                    destination = BranchDetails.objects.get(
                        booking_details=booking_details[0].destination_code
                    ).branchname
                return Response(
                    {
                        "tracking_data": tracking_data,
                        "awbno": awbno,
                        "booking": {
                            "pcs": booking_details[0].pcs,
                            "wt": booking_details[0].wt,
                            "recname": booking_details[0].recievername,
                            "date": booking_details[0].date,
                            "recphone": booking_details[0].recieverphonenumber,
                            "destination": destination,
                        },
                        "status": "success",
                    }
                )
            return Response(
                {
                    "tracking_data": tracking_data,
                    "booking": "none",
                    "status": "success",
                    "delivery_data": delivery_data,
                }
            )
        except Exception as e:
            print(e)
            return Response({"status": "error"})


class VersionAPI(APIView):
    def get(self, r):
        try:
            release = AppRelease.objects.order_by("-created_at").first()
            return Response(
                {
                    "status": "success",
                    "version": release.version,
                    "fileid": release.file_id,
                }
            )
        except Exception as e:
            print(e)
            return Response({"status": "error"})
