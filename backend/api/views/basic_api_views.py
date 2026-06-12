import json

from rest_framework import status
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
CustomTokenModel,ChildPieceDetails,
    Client
)


class UseDetails(APIView):
    def get(self, r):
        user = r.user
        if not user or user.is_anonymous:
            return Response({"error": "unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
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
                    "new_token": None,
                    "type": userdetails.type,
                    "name": userdetails.fullname(),
                    "code_name": userdetails.code_name,
                }
            )


class GetBookingDetails(APIView):
    def post(self, r):
        details = BookingDetails.objects.filter(awbno=r.data["awbno"])
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
        try:
            user = UserDetails.objects.get(user=r.user)
            branch = BranchDetails.objects.get(branch_code=user.code)
            manifest_num = branch.branch_code + '2' + branch.manifest_counter
            return Response({"manifestno": manifest_num})
        except Exception as e:
            return Response({"manifestno": None, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


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
        # try:
        #     if r.new_token != 'none':
        #         return Response({"new_token": r.new_token, "status": "new_token"})
        #     return Response({"status": "valid"})
        # except:
        #     return Response({"status": "invalid"})
        try:
            token_obj = CustomTokenModel.objects.filter(user=r.user).first()
            if token_obj:
                return Response({"status": "valid"})
            else:
                return Response({"status": "invalid"})
        except Exception as e:
            return Response({"status": "invalid"})

class Track(APIView):
    def get(self, r, awbno):
        if not awbno:
            return Response({"status": "AWB no or Reference no required"})

        try:
            # Try to find booking by AWB number first
            awb_ref = ""
            is_child_piece = False
            parent_awb = None
            search_awb = awbno  # AWB to use for tracking/delivery queries

            booking_details = BookingDetails.objects.filter(awbno=awbno)

            # If not found by AWB, check if it's a child piece number
            if not booking_details.exists():
                child_piece = ChildPieceDetails.objects.filter(child_no=awbno).first()
                if child_piece:
                    is_child_piece = True
                    parent_awb = child_piece.awbno
                    search_awb = awbno  # Use child number for tracking/delivery
                    # Get parent booking details
                    booking_details = BookingDetails.objects.filter(awbno=parent_awb)
                else:
                    # Try to find by reference number
                    booking_details = BookingDetails.objects.filter(refernce_no=awbno)

                    if booking_details.exists():
                        awb_ref = awbno
                        search_awb = booking_details[0].awbno
                    # If still not found — don't return error yet.
                    # Continue to check inscan/outscan/DRS with original awbno.
            else:
                awb_ref = booking_details[0].refernce_no

            # Get child pieces if exists (from parent AWB)
            child_pieces = []
            try:
                pcs_count = int(booking_details[0].pcs) if booking_details.exists() and booking_details[0].pcs else 0
            except (ValueError, TypeError):
                pcs_count = 0
            if pcs_count > 1:
                child_pieces = list(
                    ChildPieceDetails.objects.filter(awbno=booking_details[0].awbno)
                    .values('child_no')
                )

            # Safe code-to-name/type resolver: Branch → Hub → User → code fallback
            def resolve_name(code):
                try:
                    b = BranchDetails.objects.filter(branch_code=code).first()
                    if b: return b.branchname
                    h = HubDetails.objects.filter(hub_code=code).first()
                    if h: return h.hubname
                    u = UserDetails.objects.filter(code=code).first()
                    if u: return u.code_name
                except Exception:
                    pass
                return code

            def resolve_type(code):
                try:
                    if BranchDetails.objects.filter(branch_code=code).exists(): return 'branch'
                    if HubDetails.objects.filter(hub_code=code).exists(): return 'hub'
                    u = UserDetails.objects.filter(code=code).first()
                    if u: return u.type
                except Exception:
                    pass
                return ''

            # Tracking data collection
            tracking_data = []
            inscans = InscanModel.objects.filter(awbno=search_awb)
            if inscans:
                for inscan in inscans:
                    tracking_data.append({
                        "awbno": inscan.awbno,
                        "event": "Inscan",
                        "location": resolve_name(inscan.inscaned_branch_code),
                        "date": inscan.date,
                        "branch_type": resolve_type(inscan.inscaned_branch_code),
                    })

            outscans = OutscanModel.objects.filter(awbno=search_awb).select_related(
                "manifestnumber__vehicle_number"
            )
            if outscans:
                for outscan in outscans:
                    manifest = outscan.manifestnumber
                    tracking_data.append({
                        "awbno": outscan.awbno,
                        "event": "Outscan",
                        "location": resolve_name(manifest.inscaned_branch_code),
                        "date": manifest.date,
                        "branch_type": resolve_type(manifest.inscaned_branch_code),
                        "tohub": resolve_name(manifest.tohub_branch_code),
                    })

            tracking_data.sort(key=lambda x: x["date"])

            # Delivery data - USE search_awb (child number if tracking child)
            delivery_data = []
            drs_details = DrsDetails.objects.filter(awbno=search_awb)
            if drs_details.exists():
                drsno = DRS.objects.get(drsno=drs_details[0].drsno)
                deliverydate = ""
                deliveryimage = ""
                deliveryreason = ""
                deliveryrecname = ""
                deliveryrecphone = ""

                if drs_details[0].status:
                    deliverydetails = DeliveryDetails.objects.filter(awbno=search_awb).last()
                    deliverystatus = deliverydetails.status
                    deliverydate = deliverydetails.date
                    deliveryimage = deliverydetails.image
                    deliveryreason = deliverydetails.reason
                    deliveryrecname = deliverydetails.recievername
                    deliveryrecphone = deliverydetails.recievernumber
                else:
                    deliverystatus = "ofd"

                delivery_data.append({
                    "status": deliverystatus,
                    "deliverydate": deliverydate,
                    "deliveryimage": deliveryimage,
                    "deliveryrecname": deliveryrecname,
                    "deliveryrecphone": deliveryrecphone,
                    "deliveryreason": deliveryreason,
                })
            elif DeliveryDetails.objects.filter(awbno=search_awb).exists():
                deliverydetails = DeliveryDetails.objects.filter(awbno=search_awb).latest("date")
                delivery_data.append({
                    "status": deliverydetails.status,
                    "deliverydate": deliverydetails.date,
                    "deliveryimage": deliverydetails.image,
                    "deliveryrecname": deliverydetails.recievername,
                    "deliveryrecphone": deliverydetails.recievernumber,
                    "deliveryreason": deliverydetails.reason,
                })

            # Get destination/origin names
            destination = ""
            origin = ""
            if booking_details.exists():
                if HubDetails.objects.filter(hub_code=booking_details[0].destination_code).exists():
                    destination = HubDetails.objects.get(
                        hub_code=booking_details[0].destination_code
                    ).hubname
                elif BranchDetails.objects.filter(branch_code=booking_details[0].destination_code).exists():
                    destination = BranchDetails.objects.get(
                        branch_code=booking_details[0].destination_code
                    ).branchname

                if HubDetails.objects.filter(hub_code=booking_details[0].booked_code).exists():
                    origin = HubDetails.objects.get(
                        hub_code=booking_details[0].booked_code
                    ).hubname
                elif BranchDetails.objects.filter(branch_code=booking_details[0].booked_code).exists():
                    origin = BranchDetails.objects.get(
                        branch_code=booking_details[0].booked_code
                    ).branchname

                return Response({
                    "tracking_data": tracking_data,
                    "reference_no": awb_ref,
                    "awbno": search_awb,  # Return the actual searched AWB (child if tracking child)
                    "is_child_piece": is_child_piece,
                    "parent_awb": parent_awb if is_child_piece else None,
                    "child_pieces": child_pieces,
                    "has_children": len(child_pieces) > 0,
                    "booking": {
                        "pcs": booking_details[0].pcs,
                        "wt": booking_details[0].wt,
                        "recname": booking_details[0].recievername,
                        "date": booking_details[0].date,
                        "recphone": booking_details[0].recieverphonenumber,
                        "destination": destination,
                        "booked_hub": origin,
                        "sendername": booking_details[0].sendername,
                        "senderaddress": booking_details[0].senderaddress,
                        "senderphone": booking_details[0].senderphonenumber,
                        "recadd": booking_details[0].recieveraddress,
                        "reference": booking_details[0].refernce_no if hasattr(
                            booking_details[0], 'refernce_no'
                        ) else "",
                        "eway_bill_no": getattr(booking_details[0], 'eway_bill_no', '') or '',
                        "invoice_no": getattr(booking_details[0], 'invoice_no', '') or '',
                        "invoice_date": booking_details[0].invoice_date.strftime('%Y-%m-%d') if getattr(booking_details[0], 'invoice_date', None) else '',
                        "invoice_amount": str(booking_details[0].invoice_amount) if getattr(booking_details[0], 'invoice_amount', None) is not None else '',
                    },
                    "delivery_data": delivery_data,
                    "status": "success",
                })

            # Return whatever data was found — even if booking is missing
            if not tracking_data and not delivery_data and not booking_details.exists():
                return Response({
                    "status": "error",
                    "message": "No tracking data found for this AWB/Reference/Child Piece number"
                })

            return Response({
                "tracking_data": tracking_data,
                "awbno": search_awb,
                "booking": "none",
                "status": "success",
                "delivery_data": delivery_data,
            })

        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"status": "error", "message": str(e)})

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


class UserProfile(APIView):
    """
    Get logged-in user's profile information including branch/hub details
    """

    def get(self, request):
        try:
            user = request.user
            user_details = UserDetails.objects.get(user=user)

            # Get branch/hub information
            branch_name = ""
            branch_type = ""

            # Check if it's a hub
            related_hub_code = ""
            related_hub_name = ""
            
            if HubDetails.objects.filter(hub_code=user_details.code).exists():
                hub = HubDetails.objects.get(hub_code=user_details.code)
                branch_name = hub.hubname
                branch_type = "HUB"
            # Check if it's a branch
            elif BranchDetails.objects.filter(branch_code=user_details.code).exists():
                branch = BranchDetails.objects.get(branch_code=user_details.code)
                branch_name = branch.branchname
                branch_type = "BRANCH"
                
                # Get Related Hub Details
                related_hub_code = branch.hub
                if HubDetails.objects.filter(hub_code=related_hub_code).exists():
                    related_hub = HubDetails.objects.get(hub_code=related_hub_code)
                    related_hub_name = related_hub.hubname
                elif BranchDetails.objects.filter(branch_code=related_hub_code).exists():
                     # In case branch reports to another branch (rare but possible)
                    related_branch = BranchDetails.objects.get(branch_code=related_hub_code)
                    related_hub_name = related_branch.branchname

            profile_data = {
                "username": user.username,
                "email": user.email if user.email else "",
                "branch_code": user_details.code,
                "branch_name": branch_name,
                "branch_type": branch_type,
                "related_hub_code": related_hub_code,
                "related_hub_name": related_hub_name,
            }

            return Response({
                "status": "success",
                "data": profile_data
            }, status=status.HTTP_200_OK)

        except UserDetails.DoesNotExist:
            return Response({
                "status": "error",
                "message": "User details not found"
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"Profile error: {e}")
            return Response({
                "status": "error",
                "message": "Failed to fetch profile"
            }, status=status.HTTP_400_BAD_REQUEST)


class ClientsAPI(APIView):
    def get(self, request):
        try:
            user_details = UserDetails.objects.get(user=request.user)
            code = user_details.code
            clients = Client.objects.filter(code=code)
            data = []
            for c in clients:
                data.append({
                    "client_code": c.client_code,
                    "name": c.name,
                    "address": c.address,
                    "phone_number": c.phone_number
                })
            return Response({"status": "success", "data": data}, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        try:
            user_details = UserDetails.objects.get(user=request.user)
            code = user_details.code
            name = request.data.get("name")
            phone = request.data.get("phone")
            address = request.data.get("address")
            
            if not name or not phone or not address:
                return Response({"status": "error", "message": "All fields are required"}, status=status.HTTP_400_BAD_REQUEST)
                
            import random
            client_code = f"C{random.randint(1,999999):06d}"
            while Client.objects.filter(client_code=client_code).exists():
                client_code = f"C{random.randint(1,999999):06d}"
                
            Client.objects.create(client_code=client_code, name=name, phone_number=phone, address=address, code=code)
            return Response({"status": "success"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            print(e)
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        try:
            user_details = UserDetails.objects.get(user=request.user)
            code = user_details.code
            client_code = request.data.get("client_code")
            
            client = Client.objects.filter(client_code=client_code, code=code).first()
            if client:
                client.delete()
                return Response({"status": "success"}, status=status.HTTP_200_OK)
            return Response({"status": "error", "message": "Client not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(e)
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)