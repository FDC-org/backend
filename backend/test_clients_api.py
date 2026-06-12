import os
import django
import json
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from api.models import UserDetails, Client, BookingDetails
from api.views.basic_api_views import ClientsAPI
from api.views.Booking import Booking
from rest_framework.test import force_authenticate
from rest_framework import status

class ClientsApiTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        
        # Create user details and token/branch
        self.user = User.objects.create_user(username='testuser', password='password')
        self.user_details = UserDetails.objects.create(
            user=self.user, type='BRANCH', code='BR01', firstname='Test', lastname='User'
        )

    def test_clients_flow(self):
        # 1. Create client via POST
        data = {
            "name": "Acme Corp",
            "phone": "1234567890",
            "address": "123 Industrial Way"
        }
        request = self.factory.post('/clients/', data=json.dumps(data), content_type='application/json')
        force_authenticate(request, user=self.user)
        view = ClientsAPI.as_view()
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "success")

        # Verify database record exists
        client = Client.objects.filter(code='BR01').first()
        self.assertIsNotNone(client)
        self.assertEqual(client.name, "Acme Corp")
        client_code = client.client_code

        # 2. List clients via GET
        request_get = self.factory.get('/clients/')
        force_authenticate(request_get, user=self.user)
        response_get = view(request_get)
        self.assertEqual(response_get.status_code, status.HTTP_200_OK)
        self.assertEqual(response_get.data["status"], "success")
        self.assertEqual(len(response_get.data["data"]), 1)
        self.assertEqual(response_get.data["data"][0]["client_code"], client_code)

        # 3. Create a Booking with credit type, client_code, and billing fields
        booking_data = {
            "awbno": "1234567890",
            "date": "2026-06-12",
            "doc_type": "docx",
            "pcs": "1",
            "wt": "0.250",
            "sendername": client.name,
            "senderphone": client.phone_number,
            "senderaddress": client.address,
            "receivername": "John Doe",
            "receiverphone": "0987654321",
            "receiveraddress": "456 Residential Rd",
            "destination_code": "DEST",
            "mode": "AIR",
            "contents": "Documents",
            "pincode": "123456",
            "reference": "REF123",
            "booking_type": "credit",
            "client_code": client_code,
            "child_pieces_start": "",
            "courier_charges": "150.00",
            "gst": "27.00",
            "packing_charges": "10.00",
            "freight_charges": "50.00",
            "others": "5.00",
            "total": "242.00"
        }
        booking_request = self.factory.post('/booking/', data=json.dumps(booking_data), content_type='application/json')
        force_authenticate(booking_request, user=self.user)
        booking_view = Booking.as_view()
        booking_response = booking_view(booking_request)
        self.assertEqual(booking_response.data["status"], "success")

        # Verify booking details record is in DB
        booking_record = BookingDetails.objects.filter(awbno="1234567890").first()
        self.assertIsNotNone(booking_record)
        self.assertEqual(booking_record.booking_type, "credit")
        self.assertEqual(booking_record.client_code, client_code)
        self.assertEqual(float(booking_record.courier_charges), 150.00)
        self.assertEqual(float(booking_record.gst), 27.00)
        self.assertEqual(float(booking_record.packing_charges), 10.00)
        self.assertEqual(float(booking_record.freight_charges), 50.00)
        self.assertEqual(float(booking_record.others), 5.00)
        self.assertEqual(float(booking_record.total), 242.00)

        # 4. Delete client via DELETE
        delete_data = {
            "client_code": client_code
        }
        request_delete = self.factory.delete('/clients/', data=json.dumps(delete_data), content_type='application/json')
        force_authenticate(request_delete, user=self.user)
        response_delete = view(request_delete)
        self.assertEqual(response_delete.status_code, status.HTTP_200_OK)
        self.assertEqual(response_delete.data["status"], "success")

        # Verify client deleted in DB
        self.assertFalse(Client.objects.filter(client_code=client_code).exists())

if __name__ == "__main__":
    from django.test.runner import DiscoverRunner
    test_runner = DiscoverRunner(verbosity=2)
    failures = test_runner.run_tests(['test_clients_api'])
    if failures:
        exit(1)
