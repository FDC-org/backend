from django.core.paginator import Paginator
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import UserDetails, BookingDetails,HubDetails,BranchDetails,ChildPieceDetails


class Booking(APIView):
    def get(self, request, date):
        if not date:
            return Response(
                {"error": "date required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user_code = UserDetails.objects.get(user=request.user).code

            bookings = BookingDetails.objects.filter(
                booked_code=user_code,
                date=date
            ).order_by('-date')

            # Optimize destination lookup
            hub_map = {
                h.hub_code: h.hubname
                for h in HubDetails.objects.all()
            }

            branch_map = {
                b.branch_code: b.branchname
                for b in BranchDetails.objects.all()
            }

            data = []

            for i in bookings:
                destination_name = (
                    hub_map.get(i.destination_code)
                    or branch_map.get(i.destination_code)
                    or ""
                )

                # Get child pieces if pcs > 1
                child_pieces = []
                if int(i.pcs) > 1:
                    child_pieces = list(
                        ChildPieceDetails.objects.filter(awbno=i.awbno)
                        .values_list('child_no', flat=True)
                    )

                data.append({
                    "awbno": i.awbno,
                    "date": i.date.strftime("%d-%m-%Y"),
                    "sender": i.sendername,
                    "receiver": i.recievername,
                    "destination": destination_name,
                    "doc_type": i.doc_type,
                    "wt": i.wt,
                    "pcs": i.pcs,
                    "child_pieces": child_pieces,
                    "has_children": len(child_pieces) > 0
                })

            return Response({
                "status": "success",
                "count": len(data),
                "data": data
            })

        except Exception as e:
            print(f"ViewBookings error: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

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
        booked_code = UserDetails.objects.get(user=request.user).code
        contents = request.data['contents']
        pincode = request.data['pincode']
        reference_no = request.data['reference']
        child_piece = request.data['child_pieces_start']
        if BookingDetails.objects.filter(awbno=awbno).exists():
            return Response({"status":"exists"})
        try:
            BookingDetails.objects.create(awbno=awbno,pcs=pcs,wt=wt,sendername=sendername,
                                          recievername=receivername,senderaddress=senderaddress,
                                          recieveraddress=receiveraddress,senderphonenumber=senderphone,
                                          recieverphonenumber=receiverphone,doc_type=doc_type,
                                          destination_code=destination_code,mode=mode,date=date,
                                          booked_code=booked_code,contents=contents,pincode=pincode,refernce_no=reference_no)

            child_num = int(child_piece[-5:])
            if int(pcs) > 1:
                try:
                    for i in range(int(pcs)-1):
                        if ChildPieceDetails.objects.filter(child_no=child_piece[:-5]+str(child_num + i)).exists():
                            return Response({"status":"child exists"})
                        ChildPieceDetails.objects.create(awbno=awbno, child_no=child_piece[:-5]+str(child_num + i))
                except Exception as e:
                    print(e)
                    return Response({"status": "child exists"})
            return Response({"status":"success"})
        except Exception as e:
            print(e)
            return Response({"status":"error"})