import json
import random

from django.contrib.auth.models import User
from django.http import JsonResponse
from rest_framework.views import APIView
from ..models import HubDetails,BranchDetails,UserDetails

def generate_hub_code():
    while True:
        code = str(random.randint(100000, 999999))
        if not HubDetails.objects.filter(hub_code=code).exists():
            return code

class HubOnbaoard(APIView):
    def get(self,request):
        if request.method == 'GET':
            hubs = HubDetails.objects.all().values()
            return JsonResponse(list(hubs), safe=False)

        return JsonResponse({"error": "Invalid request method"}, status=400)

    def post(self,request):
        data = json.loads(request.body)

        hub = HubDetails.objects.create(
            hub_code=generate_hub_code(),
            location=data.get('location'),
            hubname=data.get('hubname'),
            address=data.get('address'),
            phone_number=data.get('phone_number'),
            incharge_name=data.get('incharge_name'),
            state=data.get('state'),
            region=data.get('region')
        )

        return JsonResponse({
            "message": "Hub created successfully",
            "hub_code": hub.hub_code
        }, status=201)

def generate_branch_code():
    while True:
        code = str(random.randint(100000, 999999))
        if not BranchDetails.objects.filter(branch_code=code).exists():
            return code

class BranchOnbaoard(APIView):
    def get(self, branch_code):
        if branch_code:
            try:
                branch = BranchDetails.objects.select_related('hub_code').get(branch_code=branch_code)
                hub = HubDetails.objects.get(hub_code=branch.hub)
                return JsonResponse({
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
                })
            except BranchDetails.DoesNotExist:
                return JsonResponse({"error": "Branch not found"}, status=404)

    def post(self, request):
        data = json.loads(request.body)
        hub_code = data.get('hub')
        try:
            hub = HubDetails.objects.get(hub_code=hub_code)
        except HubDetails.DoesNotExist:
            return JsonResponse({"error": "Invalid hub code"}, status=400)

        if BranchDetails.objects.filter(branch_code=data.get('branch_code')).exists():
            return JsonResponse({"error": "Branch already exists"}, status=400)
        branch_code = generate_branch_code()
        BranchDetails.objects.create(
            branch_code=branch_code,
            branchname=data.get('branchname'),
            location=data.get('location'),
            address=data.get('address'),
            phone_number=data.get('phone_number'),
            hub=hub.hub_code,
            incharge_name=data.get('incharge_name')
        )

        return JsonResponse({
            "message": "Branch onboarded successfully",
            "hub_details": {
                "hub_code": hub.hub_code,
                "hubname": hub.hubname,
                "location": hub.location,
                "state": hub.state,
                "region": hub.region,
                "branch_code":branch_code
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
    def post(self, request):
        data = json.loads(request.body)

        username = data.get('username')
        password = data.get('password')
        user_type = data.get('type')  # HUB / BRANCH / ADMIN
        code = data.get('code')
        if User.objects.filter(username=username).exists():
            return JsonResponse({"error": "Username already exists"}, status=400)

            # 👤 Create Django User
        user = User.objects.create_user(
            username=username,
            password=password
        )

        # 🔢 Generate numbers
        drs_number = generate_drs_number(code)
        manifest_number = generate_manifest_number(code)


        UserDetails.objects.create(
            user=user,
            type=user_type,
            code=code,
            firstname=data.get('firstname'),
            lastname=data.get('lastname'),
            phone_number=data.get('phone_number'),
            code_name=data.get('code_name'),
            drs_number=drs_number,
            manifestnumber=manifest_number
        )

        return JsonResponse({
            "message": "User onboarded successfully",
            "username": username,
            "drs_number": drs_number,
            "manifest_number": manifest_number
        }, status=201)
