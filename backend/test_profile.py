
import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from api.models import UserDetails, BranchDetails, HubDetails
from api.views.basic_api_views import UserProfile
from rest_framework.test import force_authenticate

class ProfileTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        
        # Create User
        self.user = User.objects.create_user(username='branch_user', password='password')
        
        # Create Hub
        self.hub = HubDetails.objects.create(
            hub_code='HUB001',
            hubname='Test Hub',
            location='Hub City',
            address='Hub Address',
            phone_number='1234567890',
            incharge_name='Hub Incharge',
            state='State',
            region='Region'
        )
        
        # Create Branch linked to Hub
        self.branch = BranchDetails.objects.create(
            branch_code='BR001',
            branchname='Test Branch',
            location='Branch City',
            address='Branch Address',
            phone_number='0987654321',
            hub='HUB001', # Linked to HUB001
            incharge_name='Branch Incharge'
        )
        
        # Link User to Branch
        self.user_details = UserDetails.objects.create(
            user=self.user,
            type='BRANCH',
            code='BR001', # Linked to BR001
            firstname='Branch',
            lastname='User',
            phone_number='1122334455',
            code_name='Test Branch User',
            manifestnumber='M001',
            drs_number='D001'
        )

    def test_branch_profile_has_hub_details(self):
        request = self.factory.get('/api/user/profile/')
        force_authenticate(request, user=self.user)
        view = UserProfile.as_view()
        response = view(request)
        
        print("Profile Response Data:", response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['branch_code'], 'BR001')
        self.assertEqual(response.data['data']['branch_name'], 'Test Branch')
        self.assertEqual(response.data['data']['branch_type'], 'BRANCH')
        
        # Verify Related Hub fields
        self.assertEqual(response.data['data']['related_hub_code'], 'HUB001')
        self.assertEqual(response.data['data']['related_hub_name'], 'Test Hub')

if __name__ == "__main__":
    from django.test.runner import DiscoverRunner
    test_runner = DiscoverRunner(verbosity=2)
    failures = test_runner.run_tests(['test_profile'])
    if failures:
        exit(1)
