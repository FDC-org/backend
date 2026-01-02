import datetime
import json

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

from ..models import UserDetails, DrsDetails, DRS, DeliveryBoyDetalis, DeliveryDetails, deliverdordrs, Locations, \
    BookingDetails


class DRSapi(APIView):
    def get(self, r,date):
        if not date:
            return Response({'status': 'not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        drsdetails = DRS.objects.filter(date__date=date,code = UserDetails.objects.get(user=r.user).code)
        data = []
        for i in drsdetails:
            s = "ofd"
            awbdata = []
            for awbno in DrsDetails.objects.filter(drsno=i.drsno):
                s = "ofd"
                if awbno.status:
                    d = DeliveryDetails.objects.filter(awbno=awbno.awbno)
                    if d.exists():
                        s = d[0].status
                name = ""
                pcs = ""
                wt = ""
                adata = BookingDetails.objects.filter(awbno=awbno.awbno)
                if adata.exists():
                    pcs = adata[0].pcs
                    wt = adata[0].wt
                    name = adata[0].recievername
                awbdata.append({"awbno":awbno.awbno,"status":s,"pcs":pcs,"wt":wt,"receiver_name":name})
            data.append({"date": i.date,"drsno":i.drsno,"boy":DeliveryBoyDetalis.objects.get(boy_code=i.boycode).name,
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
            drs = DRS.objects.create(date=dt_naive, boycode=delivery_boy,
                               code=branch.code, drsno=branch.drs_number, location=lcoation)
            for no in awbno:
                DrsDetails.objects.create(drsno =drs.drsno, awbno = no)
                deliverdordrs.objects.create(awbno = no)
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
            for i in awbno:
                if deliverdordrs.objects.filter(awbno=i).exists():
                    i.delete()
            return Response({"status":"error"},status=status.HTTP_400_BAD_REQUEST)

class Delivered(APIView):
    def get(self, r):
        return Response({"status":"method not allowed"},status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def post(self, r):
        awbno = r.data['awbno']
        if awbno:
            awbno = json.loads(awbno)
        else:
            return Response({"status":"invalid awbno"},status=status.HTTP_400_BAD_REQUEST)
        awbstatus = r.data['status'].strip().lower()
        try:
            dd = DeliveryDetails.objects.filter(awbno=awbno)
            if  dd.exists():
                dd[0].status = awbstatus
                dd[0].save()
                return Response({"status":"success"},status=status.HTTP_201_CREATED)
            if awbstatus == 'delivered':
                receivername = r.data['receivername']
                receivernumber = r.data['receivernumber']
                image = r.FILES.get('image')
                date = r.data['date']
                for awb in awbno:
                    image_url  = upload_file(image,'pod')
                    DeliveryDetails.objects.create(awbno = awb,status = 'delivered',recievername = receivername,image = image_url,recievernumber=receivernumber,date= date)
                    dd = DrsDetails.objects.filter(awbno=awbno)
                    if dd.exists():
                        dd[0].status = True
                        dd[0].save()
            elif awbstatus == 'undelivered' or  awbstatus == 'rto':
                date = r.data['date']
                reason = r.data['reason']
                statusre = "undelivered" if awbstatus == 'undelivered' else "rto"
                for awb in awbno:
                    deliverdordrs.objects.filter(awbno=awb).delete()
                    DeliveryDetails.objects.create(awbno=awb, status=statusre, reason=reason,date=date)
                    dd = DrsDetails.objects.filter(awbno=awbno)
                    if dd.exists():
                        dd[0].status = True
                        dd[0].save()
            else:
                return Response({"status":"invalid status"}, status=awbstatus.HTTP_400_BAD_REQUEST)
            return Response({"status":"success",}, status=status.HTTP_201_CREATED)
        except Exception as e:
            print(e)
            DeliveryDetails.objects.filter(awbno=awbno).delete()
            return Response({"status":"error"},status=status.HTTP_400_BAD_REQUEST)


class getDeliveryBoys_locations(APIView):
    def get(self, r):
        data = []
        boydata = []
        locdata = []
        for i in DeliveryBoyDetalis.objects.filter(code = UserDetails.objects.get(user=r.user).code):
            boydata.append({'boy_code':i.boy_code,'name':i.name})
        for i in Locations.objects.filter(code = UserDetails.objects.get(user=r.user).code):
            locdata.append({'loc_code':i.location_code,'location':i.location})
        data.append({'boy_code':boydata,'location':locdata})
        return Response({"status":"success","data":data},status=status.HTTP_200_OK)
    # def post(self,r):
    #     boycode = r.data['boy_code']
    #     location = r.data['location']



def upload_file(file,drsno):

    # Configuration
    cloudinary.config(
        cloud_name="di9u2ri58",
        api_key="631486297826291",
        api_secret="8GtAsx1lGtkxj9-YOD-58eHWLJg",  # Click 'View API Keys' above to copy your API secret
        secure=True
    )

    # Upload an image
    upload_result = cloudinary.uploader.upload(file,
                                               public_id=drsno)
    print(upload_result["secure_url"])

    # Optimize delivery by resizing and applying auto-format and auto-quality
    optimize_url, _ = cloudinary_url("shoes", fetch_format="auto", quality="auto")
    print(optimize_url)

    return optimize_url