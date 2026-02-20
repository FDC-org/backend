import json
import random

from django.contrib.auth.models import User
from django.http import JsonResponse
from rest_framework.views import APIView
from ..models import HubDetails,BranchDetails,UserDetails, DeliveryBoyDetalis
from ..permissions import IsAdminOrSuperUser

def generate_hub_code():
    while True:
        code = str(random.randint(100000, 999999))
        if not HubDetails.objects.filter(hub_code=code).exists():
            return code

class HubOnbaoard(APIView):
    permission_classes = [IsAdminOrSuperUser]

    def get(self, request):
        hubs = HubDetails.objects.all()
        hub_list = []
        for hub in hubs:
            hub_list.append({
                "hubname": hub.hubname,
                "hub_code": hub.hub_code,
                "location": hub.location,
                "address": hub.address,
                "phone_number": hub.phone_number,
                "incharge_name": hub.incharge_name,
                "state": hub.state,
                "region": hub.region
            })
        return JsonResponse({"status": "success", "data": hub_list}, safe=False)

    def post(self, request):
        data = json.loads(request.body)
        hub_code = generate_hub_code()
        hub = HubDetails.objects.create(
            hub_code=hub_code,
            location=data.get('location'),
            hubname=data.get('hubname'),
            address=data.get('address'),
            phone_number=data.get('phone_number'),
            incharge_name=data.get('incharge_name'),
            state=data.get('state'),
            region=data.get('region')
        )

        return JsonResponse({
            "status": "success",
            "message": "Hub created successfully",
            "data": {
                "hub_code": hub.hub_code,
                "hubname": hub.hubname,
                "location": hub.location,
                "address": hub.address,
                "phone_number": hub.phone_number,
                "incharge_name": hub.incharge_name,
                "state": hub.state,
                "region": hub.region
            }
        }, status=201)

def generate_branch_code():
    while True:
        code = str(random.randint(100000, 999999))
        if not BranchDetails.objects.filter(branch_code=code).exists():
            return code

class BranchOnbaoard(APIView):
    permission_classes = [IsAdminOrSuperUser]

    def get(self, request, branch_code=None):
        if branch_code:
            try:
                branch = BranchDetails.objects.get(branch_code=branch_code)
                hub = HubDetails.objects.get(hub_code=branch.hub)
                return JsonResponse({
                    "status": "success",
                    "data": {
                        "branch_code": branch.branch_code,
                        "branch_name": branch.branchname,
                        "location": branch.location,
                        "address": branch.address,
                        "phone_number": branch.phone_number,
                        "incharge_name": branch.incharge_name,
                        "state": hub.state,
                        "region": hub.region,
                        "hub_code": hub.hub_code,
                        "hub_name": hub.hubname
                    }
                })
            except BranchDetails.DoesNotExist:
                return JsonResponse({"status": "error", "message": "Branch not found"}, status=404)
        
        # List all branches
        branches = BranchDetails.objects.all()
        branch_list = []
        for branch in branches:
            hub_name = ""
            try:
                hub = HubDetails.objects.get(hub_code=branch.hub)
                hub_name = hub.hubname
            except HubDetails.DoesNotExist:
                pass
                
            branch_list.append({
                "branchname": branch.branchname,
                "branch_code": branch.branch_code,
                "hub": branch.hub,
                "hub_name": hub_name,
                "location": branch.location,
                "address": branch.address,
                "phone_number": branch.phone_number,
                "incharge_name": branch.incharge_name
            })
        return JsonResponse({"status": "success", "data": branch_list}, safe=False)

    def post(self, request):
        data = json.loads(request.body)
        hub_code = data.get('hub')
        try:
            hub = HubDetails.objects.get(hub_code=hub_code)
        except HubDetails.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Invalid hub code"}, status=400)

        branch_code = generate_branch_code()
        branch = BranchDetails.objects.create(
            branch_code=branch_code,
            branchname=data.get('branchname'),
            location=data.get('location'),
            address=data.get('address'),
            phone_number=data.get('phone_number'),
            hub=hub.hub_code,
            incharge_name=data.get('incharge_name')
        )

        return JsonResponse({
            "status": "success",
            "message": "Branch onboarded successfully",
            "data": {
                "branch_code": branch.branch_code,
                "branchname": branch.branchname,
                "location": branch.location,
                "address": branch.address,
                "phone_number": branch.phone_number,
                "hub": branch.hub,
                "hub_name": hub.hubname,
                "incharge_name": branch.incharge_name
            }
        }, status=201)


import random
from django.utils import timezone

def generate_unique_number():
    return str(random.randint(1000, 9999))

def generate_drs_number(code):
    year = timezone.now().strftime('%y')
    return f"{year}{generate_unique_number()}{code}01001"

def generate_manifest_number(code):
    year = timezone.now().strftime('%y')
    return f"{year}{generate_unique_number()}{code}02001"


class UserOnboard(APIView):
    permission_classes = [IsAdminOrSuperUser]

    def get(self, request):
        users = UserDetails.objects.all()
        user_list = []
        for user_detail in users:
            user_list.append({
                "username": user_detail.user.username,
                "type": user_detail.type,
                "code": user_detail.code,
                "code_name": user_detail.code_name,
                "firstname": user_detail.firstname,
                "lastname": user_detail.lastname,
                "phone_number": user_detail.phone_number
            })
        return JsonResponse({"status": "success", "data": user_list}, safe=False)

    def post(self, request):
        data = json.loads(request.body)

        username = data.get('username')
        password = data.get('password')
        user_type = data.get('type')  # HUB / BRANCH / ADMIN
        code = data.get('code')
        if User.objects.filter(username=username).exists():
            return JsonResponse({"status": "error", "message": "Username already exists"}, status=400)

        # 👤 Create Django User
        user = User.objects.create_user(
            username=username,
            password=password
        )

        # 🔢 Generate numbers (Only if needed, usually for non-admin)
        drs_number = generate_drs_number(code) if code else ""
        manifest_number = generate_manifest_number(code) if code else ""

        user_detail = UserDetails.objects.create(
            user=user,
            type=user_type,
            code=code if code else "ADMIN",
            firstname=data.get('firstname'),
            lastname=data.get('lastname'),
            phone_number=data.get('phone_number'),
            code_name=data.get('code_name'),
            drs_number=drs_number,
            manifestnumber=manifest_number
        )

        return JsonResponse({
            "status": "success",
            "message": "User onboarded successfully",
            "data": {
                "username": username,
                "type": user_type,
                "code": code,
                "firstname": user_detail.firstname,
                "lastname": user_detail.lastname,
                "drs_number": drs_number,
                "manifest_number": manifest_number
            }
        }, status=201)

def generate_boy_code():
    while True:
        code = str(random.randint(100000, 999999))
        if not DeliveryBoyDetalis.objects.filter(boy_code=code).exists():
            return code

class EmployeeOnboard(APIView):
    permission_classes = [IsAdminOrSuperUser]

    def get(self, request):
        employees = DeliveryBoyDetalis.objects.all()
        employee_list = []
        for emp in employees:
            unit_name = ""
            # Check if it's a Hub
            try:
                hub = HubDetails.objects.get(hub_code=emp.code)
                unit_name = hub.hubname
            except HubDetails.DoesNotExist:
                # Check if it's a Branch
                try:
                    branch = BranchDetails.objects.get(branch_code=emp.code)
                    unit_name = branch.branchname
                except BranchDetails.DoesNotExist:
                    pass

            employee_list.append({
                "name": emp.name,
                "phone_number": emp.phone_number,
                "address": emp.address,
                "code": emp.code,
                "unit_name": unit_name
            })
        return JsonResponse({"status": "success", "data": employee_list}, safe=False)

    def post(self, request):
        data = json.loads(request.body)
        
        # Verify related hub/branch code exists
        code = data.get('code')
        
        boy_code = generate_boy_code()
        
        emp = DeliveryBoyDetalis.objects.create(
            boy_code=boy_code,
            name=data.get('name'),
            address=data.get('address', ''),
            phone_number=data.get('phone_number'),
            code=code
        )
        
        # Determine unit name for the response
        unit_name = ""
        try:
            hub = HubDetails.objects.get(hub_code=code)
            unit_name = hub.hubname
        except HubDetails.DoesNotExist:
            try:
                branch = BranchDetails.objects.get(branch_code=code)
                unit_name = branch.branchname
            except BranchDetails.DoesNotExist:
                pass

        return JsonResponse({
            "status": "success",
            "message": "Employee onboarded successfully",
            "data": {
                "boy_code": emp.boy_code,
                "name": emp.name,
                "phone_number": emp.phone_number,
                "address": emp.address,
                "code": emp.code,
                "unit_name": unit_name
            }
        }, status=201)
