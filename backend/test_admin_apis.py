
import os
import django
import json
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from api.models import UserDetails
from api.views.onboarding import HubOnbaoard, UserOnboard, EmployeeOnboard
from rest_framework.test import force_authenticate

class AdminApiTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        
        # 1. Create Regular User (Non-Admin)
        self.regular_user = User.objects.create_user(username='regular', password='password')
        UserDetails.objects.create(user=self.regular_user, type='BRANCH', code='BR01', firstname='Reg', lastname='User')

        # 2. Create Admin User
        self.admin_user = User.objects.create_user(username='admin', password='password')
        UserDetails.objects.create(user=self.admin_user, type='ADMIN', code='AD01', firstname='Admin', lastname='User')
        
        # 3. Create Superuser
        self.superuser = User.objects.create_superuser(username='super', password='password', email='super@example.com')

    def test_hub_onboard_permission(self):
        # Data for Hub
        data = {
            "hubname": "Test Hub",
            "location": "Test Loc",
            "address": "Test Addr",
            "phone_number": "123", 
            "incharge_name": "Incharge",
            "state": "State",
            "region": "Region"
        }
        request = self.factory.post('/onboard/hub/', data=json.dumps(data), content_type='application/json')
        
        # Case A: Regular User -> Should fail (403)
        force_authenticate(request, user=self.regular_user)
        view = HubOnbaoard.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 403, "Regular user should be forbidden")
        
        # Case B: Admin User -> Should success (201)
        force_authenticate(request, user=self.admin_user)
        response = view(request)
        self.assertEqual(response.status_code, 201, "Admin user should be allowed")
        
        # Case C: Superuser -> Should success (201)
        force_authenticate(request, user=self.superuser)
        response = view(request)
        self.assertEqual(response.status_code, 201, "Superuser should be allowed")

    def test_employee_onboard_permission(self):
         # Data for Employee
        data = {
            "name": "Test Emp",
            "address": "Emp Addr",
            "phone_number": "999",
            "code": "HUB001"
        }
        request = self.factory.post('/onboard/employee/', data=json.dumps(data), content_type='application/json')
        
         # Case A: Regular User -> Should fail (403)
        force_authenticate(request, user=self.regular_user)
        view = EmployeeOnboard.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 403)

         # Case B: Admin User -> Should success (201)
        force_authenticate(request, user=self.admin_user)
        response = view(request)
        self.assertEqual(response.status_code, 201)

if __name__ == "__main__":
    from django.test.runner import DiscoverRunner
    test_runner = DiscoverRunner(verbosity=2)
    failures = test_runner.run_tests(['test_admin_apis'])
    if failures:
        exit(1)
