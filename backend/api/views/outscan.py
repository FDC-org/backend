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
            if HubDetails.objects.filter(hubname=tohub).exists():
                tohubde = HubDetails.objects.get(hubname=tohub)
                tohub = tohubde.hub_code

            elif BranchDetails.objects.filter(branchname=tohub).exists():
                tobranchde = BranchDetails.objects.get(branchname=tohub)
                tohub = tobranchde.branch_code
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
        vehicle_number = r.data.get('vehicle_number')
        tohub = r.data["tohub"]
        branch_code = UserDetails.objects.get(user=r.user)
        date = r.data["date"]
        try:
            dt_naive = datetime.datetime.strptime(date, "%d-%m-%Y, %H:%M:%S")

            if HubDetails.objects.filter(hubname=tohub).exists():
                tohubde = HubDetails.objects.get(hubname=tohub)
                tohub = tohubde.hub_code

            if BranchDetails.objects.filter(branchname=tohub).exists():
                tobranchde = BranchDetails.objects.get(branchname=tohub)
                tohub = tobranchde.branch_code
            vehicle = Vehicle_Details.objects.filter(
                    vehiclenumber=vehicle_number)
            if vehicle.exists():
                vehicle = Vehicle_Details.objects.get(
                    vehiclenumber=vehicle_number)
            else:
                vehicle = None
            manifest = ManifestDetails.objects.create(
                date=dt_naive,
                inscaned_branch_code=branch_code.code,
                tohub_branch_code=UserDetails.objects.get(code=tohub).code,
                manifestnumber=manifest_number,
                vehicle_number=vehicle,
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


class DownloadManifestPDF(APIView):
    """
    Download Manifest PDF directly (Generated on-the-fly)
    GET /api/manifest/download/{manifest_number}/
    No authentication required for direct download links
    """
    authentication_classes = []  # Allow unauthenticated access
    permission_classes = []  # No permission required
    
    def get(self, request, manifest_number):
        try:
            from django.http import HttpResponse
            from ..utils.pdf_generator import get_manifest_data, generate_manifest_pdf, generate_error_pdf
            
            # Get Manifest Data
            manifest_data = get_manifest_data(manifest_number)
            
            if not manifest_data:
                # Generate Error PDF for not found
                error_pdf = generate_error_pdf(f"Manifest {manifest_number} not found or data missing")
                if error_pdf:
                    response = HttpResponse(error_pdf, content_type='application/pdf')
                    response['Content-Disposition'] = f'attachment; filename="Error_Manifest_{manifest_number}.pdf"'
                    response['Content-Length'] = len(error_pdf)
                    return response
                return Response({"status": "error", "message": "Manifest not found"}, 
                              status=status.HTTP_404_NOT_FOUND)
            
            # Generate PDF
            pdf_bytes = generate_manifest_pdf(manifest_data)
            
            if pdf_bytes:
                # Create HTTP response with PDF
                response = HttpResponse(pdf_bytes, content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="Manifest_{manifest_number}.pdf"'
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
                    response['Content-Disposition'] = f'attachment; filename="Error_Manifest_{manifest_number}.pdf"'
                    response['Content-Length'] = len(error_pdf)
                    return response
            except:
                pass
            
            # Fallback to JSON error if everything fails
            return Response({"status": "error", "message": str(e)}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ViewManifestPDF(APIView):
    """
    View Manifest PDF inline in browser (Generated on-the-fly)
    GET /api/manifest/view/{manifest_number}/
    No authentication required for viewing
    """
    authentication_classes = []  # Allow unauthenticated access
    permission_classes = []  # No permission required
    
    def get(self, request, manifest_number):
        try:
            from django.http import HttpResponse
            from ..utils.pdf_generator import get_manifest_data, generate_manifest_pdf, generate_error_pdf
            
            # Get Manifest Data
            manifest_data = get_manifest_data(manifest_number)
            
            if not manifest_data:
                 # Generate Error PDF for not found
                error_pdf = generate_error_pdf(f"Manifest {manifest_number} not found or data missing")
                if error_pdf:
                    response = HttpResponse(error_pdf, content_type='application/pdf')
                    response['Content-Disposition'] = f'inline; filename="Error_Manifest_{manifest_number}.pdf"'
                    response['Content-Length'] = len(error_pdf)
                    return response
                return Response({"status": "error", "message": "Manifest not found"}, 
                              status=status.HTTP_404_NOT_FOUND)
            
            # Generate PDF
            pdf_bytes = generate_manifest_pdf(manifest_data)
            
            if pdf_bytes:
                # Create HTTP response with PDF for inline viewing
                response = HttpResponse(pdf_bytes, content_type='application/pdf')
                response['Content-Disposition'] = f'inline; filename="Manifest_{manifest_number}.pdf"'
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
                    response['Content-Disposition'] = f'inline; filename="Error_Manifest_{manifest_number}.pdf"'
                    response['Content-Length'] = len(error_pdf)
                    return response
            except:
                pass
                
            return Response({"status": "error", "message": str(e)}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)

