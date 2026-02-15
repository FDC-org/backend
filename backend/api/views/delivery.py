import datetime
import json
import random
import uuid

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
            data.append({
                "date": i.date,
                "drsno":i.drsno,
                "boy":DeliveryBoyDetalis.objects.get(boy_code=i.boycode).name,
                "location":Locations.objects.get(location_code=i.location).location,
                "awbdata":awbdata,
                "document_url": i.document_url  # Include PDF URL
            })
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
            
            # Generate and upload PDF
            try:
                from ..utils.pdf_generator import generate_and_upload_drs_pdf
                from ..models import BranchDetails, HubDetails
                
                # Get delivery boy name
                delivery_boy_name = DeliveryBoyDetalis.objects.get(boy_code=delivery_boy).name
                
                # Get location name
                location_name = Locations.objects.get(location_code=lcoation).location
                
                # Get branch details
                branch_details = None
                if BranchDetails.objects.filter(branch_code=branch.code).exists():
                    branch_details = BranchDetails.objects.get(branch_code=branch.code)
                    branch_name = branch_details.branchname
                    branch_address = f"{branch_details.address}, {branch_details.location}"
                else:
                    branch_name = branch.code_name
                    branch_address = ""
                
                # Prepare AWB items data
                awb_items = []
                for awb in awbno:
                    booking = BookingDetails.objects.filter(awbno=awb).first()
                    if booking:
                        awb_items.append({
                            'center': booking.destination_code or branch.code_name,
                            'doc_type': booking.doc_type or 'NON-DOX',
                            'awb_number': awb,
                            'party_name': booking.recievername or '',
                            'party_phone': booking.recieverphonenumber or '',
                            'pieces': booking.pcs or 0,
                            'weight': float(booking.wt) if booking.wt else 0.0,
                            'remarks': booking.contents or ''
                        })
                    else:
                        awb_items.append({
                            'center': branch.code_name,
                            'doc_type': 'NON-DOX',
                            'awb_number': awb,
                            'party_name': '',
                            'party_phone': '',
                            'pieces': 0,
                            'weight': 0.0,
                            'remarks': ''
                        })
                
                # Prepare DRS data for PDF
                drs_data = {
                    'drs_number': drs.drsno,
                    'branch_name': branch_name,
                    'branch_address': branch_address,
                    'date': dt_naive.strftime('%d/%m/%Y %H:%M:%S'),
                    'area': location_name,
                    'delivery_boy': delivery_boy_name,
                    'awb_items': awb_items
                }
                
                # Generate and upload PDF
                pdf_url = generate_and_upload_drs_pdf(drs_data)
                
                # Update DRS with PDF URL
                drs.document_url = pdf_url
                drs.save()
                
                return Response({
                    "status": "success",
                    "drs_number": drs.drsno,
                    "document_url": pdf_url
                }, status=status.HTTP_201_CREATED)
                
            except Exception as pdf_error:
                print(f"PDF generation error: {pdf_error}")
                # DRS still created, just without PDF
                return Response({
                    "status": "success",
                    "drs_number": drs.drsno,
                    "document_url": None,
                    "pdf_error": str(pdf_error)
                }, status=status.HTTP_201_CREATED)
                
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
                    deliverdordrs.objects.filter(awbno=i)[0].delete()
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
            receivername = r.data.get('receivername')
            receivernumber = r.data.get('receivernumber')
            image = r.FILES.get('image')
            date = r.data['date']
            reason = r.data.get('reason')
            image_url = ""
            if awbstatus == 'delivered':
                image_url = upload_file(image, str(uuid.uuid4().hex))
            for awb in awbno:
                dd = DeliveryDetails.objects.filter(awbno=awb)
                if  dd.exists():
                    if dd[0].status =='delivered':
                        return Response({"status":"already delivered"},status=status.HTTP_201_CREATED)
                if awbstatus == 'delivered':
                    DeliveryDetails.objects.create(awbno = awb,status = 'delivered',recievername = receivername,image = image_url,recievernumber=receivernumber,date= date)
                    dd = DrsDetails.objects.filter(awbno=awb).first()
                    if dd:
                        dd.status = True
                        dd.save()
                elif awbstatus == 'undelivered' or  awbstatus == 'rto':
                    date = r.data['date']
                    statusre = "undelivered" if awbstatus == 'undelivered' else "rto"
                    deliverdordrs.objects.filter(awbno=awb).delete()
                    DeliveryDetails.objects.create(awbno=awb, status=statusre, reason=reason,date=date)
                    dd = DrsDetails.objects.filter(awbno=awb).first()
                    if dd:
                        dd.status = True
                        dd.save()
                else:
                    return Response({"status":"invalid status"}, status=status.HTTP_400_BAD_REQUEST)
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


class AddDeliveryBoys(APIView):
    def get(self,r):
        code = UserDetails.objects.get(user = r.user).code
        data =[]
        try:
            if DeliveryBoyDetalis.objects.filter(code=code).exists():
                for i in DeliveryBoyDetalis.objects.filter(code=code):
                    data.append({'boy_code':i.boy_code,'name':i.name,"phone_number":i.phone_number})
                return Response({"status":"success","data":data},status=status.HTTP_200_OK)
            return Response({"status":"success","data":data},status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response({"status":"error"},status=status.HTTP_400_BAD_REQUEST)
    def post(self, r):
        boycode = f"B{random.randint(1,999999):06d}"
        boyname = r.data['boyname']
        phone = r.data['phone']
        address = r.data['address']
        code = UserDetails.objects.get(user=r.user).code
        try:
            while DeliveryBoyDetalis.objects.filter(boy_code=boycode).exists():
                boycode = f"B{random.randint(1, 999999):06d}"
            DeliveryBoyDetalis.objects.create(boy_code=boycode,name=boyname,phone_number=phone,address=address,code=code)
            return Response({"status":"success"},status=status.HTTP_201_CREATED)
        except Exception as e:
            print(e)
            return Response({"status":"error"},status=status.HTTP_400_BAD_REQUEST)

class AddAreas(APIView):
    def get(self,r):
        code = UserDetails.objects.get(user=r.user).code
        data = []
        try:
            if Locations.objects.filter(code=code).exists():
                for i in Locations.objects.filter(code=code):
                    data.append({'area_code': i.location_code, 'area': i.location})
                return Response({"status": "success", "data": data}, status=status.HTTP_200_OK)
            return Response({"status": "success", "data": data}, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response({"status": "error"}, status=status.HTTP_400_BAD_REQUEST)
    def post(self, r):
        area = r.data['area']
        area_code = f"A{random.randint(1,999999):06d}"
        code = UserDetails.objects.get(user=r.user).code
        try:
            while Locations.objects.filter(location_code=area_code).exists():
                area_code = f"A{random.randint(1, 999999):06d}"
            Locations.objects.create(code=code,location=area,location_code=area_code)
            return Response({"status":"success"},status=status.HTTP_201_CREATED)
        except Exception as e:
            print(e)
            return Response({"status":"error"},status=status.HTTP_400_BAD_REQUEST)

def upload_file(file,drsno):
    # Kept for backward compatibility if needed, or can be removed
    import cloudinary
    import cloudinary.uploader
    from cloudinary.utils import cloudinary_url

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
    optimize_url, _ = cloudinary_url(upload_result["secure_url"], fetch_format="auto", quality="auto")
    print(optimize_url)

    return optimize_url


class DownloadDRSPDF(APIView):
    """
    Download DRS PDF directly (Generated on-the-fly)
    GET /api/drs/download/{drs_number}
    No authentication required for direct download links
    """
    authentication_classes = []  # Allow unauthenticated access
    permission_classes = []  # No permission required
    
    def get(self, request, drs_number):
        try:
            from django.http import HttpResponse
            from ..utils.pdf_generator import get_drs_data, generate_drs_pdf, generate_error_pdf
            
            # Get DRS Data
            drs_data = get_drs_data(drs_number)
            
            if not drs_data:
                # Generate Error PDF for not found
                error_pdf = generate_error_pdf(f"DRS {drs_number} not found or data missing")
                if error_pdf:
                    response = HttpResponse(error_pdf, content_type='application/pdf')
                    response['Content-Disposition'] = f'attachment; filename="Error_DRS_{drs_number}.pdf"'
                    response['Content-Length'] = len(error_pdf)
                    return response
                return Response({"status": "error", "message": "DRS not found"}, 
                              status=status.HTTP_404_NOT_FOUND)
            
            # Generate PDF
            pdf_bytes = generate_drs_pdf(drs_data)
            
            if pdf_bytes:
                # Create HTTP response with PDF
                response = HttpResponse(pdf_bytes, content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="DRS_{drs_number}.pdf"'
                response['Content-Length'] = len(pdf_bytes)
                return response
            else:
                raise Exception("Failed to generate PDF bytes")
                
        except Exception as e:
            # Generate Error PDF
            try:
                from ..utils.pdf_generator import generate_error_pdf
                error_pdf = generate_error_pdf(f"Error generating PDF: {str(e)}")
                if error_pdf:
                    response = HttpResponse(error_pdf, content_type='application/pdf')
                    response['Content-Disposition'] = f'attachment; filename="Error_DRS_{drs_number}.pdf"'
                    response['Content-Length'] = len(error_pdf)
                    return response
            except:
                pass
            
            # Fallback to JSON error if everything fails
            return Response({"status": "error", "message": str(e)}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ViewDRSPDF(APIView):
    """
    View DRS PDF inline in browser (Generated on-the-fly)
    GET /api/drs/view/{drs_number}/
    No authentication required for viewing
    """
    authentication_classes = []  # Allow unauthenticated access
    permission_classes = []  # No permission required
    
    def get(self, request, drs_number):
        try:
            from django.http import HttpResponse
            from ..utils.pdf_generator import get_drs_data, generate_drs_pdf, generate_error_pdf
            
            # Get DRS Data
            drs_data = get_drs_data(drs_number)
            
            if not drs_data:
                 # Generate Error PDF for not found
                error_pdf = generate_error_pdf(f"DRS {drs_number} not found or data missing")
                if error_pdf:
                    response = HttpResponse(error_pdf, content_type='application/pdf')
                    response['Content-Disposition'] = f'inline; filename="Error_DRS_{drs_number}.pdf"'
                    response['Content-Length'] = len(error_pdf)
                    return response
                return Response({"status": "error", "message": "DRS not found"}, 
                              status=status.HTTP_404_NOT_FOUND)
            
            # Generate PDF
            pdf_bytes = generate_drs_pdf(drs_data)
            
            if pdf_bytes:
                # Create HTTP response with PDF for inline viewing
                response = HttpResponse(pdf_bytes, content_type='application/pdf')
                response['Content-Disposition'] = f'inline; filename="DRS_{drs_number}.pdf"'
                response['Content-Length'] = len(pdf_bytes)
                return response
            else:
                 raise Exception("Failed to generate PDF bytes")
                
        except Exception as e:
            # Generate Error PDF
            try:
                from ..utils.pdf_generator import generate_error_pdf
                error_pdf = generate_error_pdf(f"Error viewing PDF: {str(e)}")
                if error_pdf:
                    response = HttpResponse(error_pdf, content_type='application/pdf')
                    response['Content-Disposition'] = f'inline; filename="Error_DRS_{drs_number}.pdf"'
                    response['Content-Length'] = len(error_pdf)
                    return response
            except:
                pass
                
            return Response({"status": "error", "message": str(e)}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)

