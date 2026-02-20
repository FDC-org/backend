
import os
import django
import json
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from api.models import UserDetails, HubDetails, BranchDetails, DeliveryBoyDetalis
from api.views.onboarding import HubOnbaoard, BranchOnbaoard, UserOnboard, EmployeeOnboard
from rest_framework.test import force_authenticate

class RefinedApiTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        
        # Create Admin User
        self.admin_user = User.objects.create_user(username='admin', password='password')
        UserDetails.objects.create(user=self.admin_user, type='ADMIN', code='AD01', firstname='Admin', lastname='User')
        
    def test_hub_api(self):
        # POST
        data = {
            "hubname": "Delhi Hub",
            "location": "Delhi",
            "address": "Okhla",
            "phone_number": "1234567890",
            "incharge_name": "Incharge Delhi",
            "state": "Delhi",
            "region": "North"
        }
        request = self.factory.post('/api/onboard/hub/', data=json.dumps(data), content_type='application/json')
        force_authenticate(request, user=self.admin_user)
        response = HubOnbaoard.as_view()(request)
        self.assertEqual(response.status_code, 201)
        res_data = json.loads(response.content)
        self.assertEqual(res_data['status'], 'success')
        hub_code = res_data['data']['hub_code']

        # GET
        request = self.factory.get('/api/onboard/hub/')
        force_authenticate(request, user=self.admin_user)
        response = HubOnbaoard.as_view()(request)
        self.assertEqual(response.status_code, 200)
        res_data = json.loads(response.content)
        self.assertEqual(res_data['status'], 'success')
        self.assertTrue(len(res_data['data']) >= 1)
        self.assertEqual(res_data['data'][0]['hub_code'], hub_code)

    def test_branch_api(self):
        # Create Hub first
        hub = HubDetails.objects.create(hub_code='HUB01', hubname='Hub Name', location='Loc')

        # POST
        data = {
            "branchname": "Branch 1",
            "hub": "HUB01",
            "location": "Loc 1",
            "address": "Addr 1",
            "phone_number": "111",
            "incharge_name": "Inc 1"
        }
        request = self.factory.post('/api/onboard/branch/', data=json.dumps(data), content_type='application/json')
        force_authenticate(request, user=self.admin_user)
        response = BranchOnbaoard.as_view()(request)
        self.assertEqual(response.status_code, 201)
        res_data = json.loads(response.content)
        self.assertEqual(res_data['status'], 'success')
        self.assertEqual(res_data['data']['hub_name'], 'Hub Name')

        # GET
        request = self.factory.get('/api/onboard/branch/')
        force_authenticate(request, user=self.admin_user)
        response = BranchOnbaoard.as_view()(request)
        self.assertEqual(response.status_code, 200)
        res_data = json.loads(response.content)
        self.assertEqual(res_data['status'], 'success')
        self.assertTrue(len(res_data['data']) >= 1)
        self.assertEqual(res_data['data'][0]['hub_name'], 'Hub Name')

if __name__ == "__main__":
    from django.test.runner import DiscoverRunner
    test_runner = DiscoverRunner(verbosity=1)
    failures = test_runner.run_tests(['test_refined_onboarding'])
    if failures:
        exit(1)
