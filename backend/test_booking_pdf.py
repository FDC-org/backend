# Setup Django
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.test import RequestFactory
from django.urls import reverse
from rest_framework.test import APIClient
import datetime
from decimal import Decimal

from api.models import BookingDetails, UserDetails
from api.utils.pdf_generator import generate_booking_pdf, get_booking_data
from api.views.booking_pdf import download_booking_pdf

def test_booking_pdf():
    print("Testing Booking PDF Generation...")
    
    # thorough setup of dummy data
    awb = "LR_TEST_1"
    
    # Create dummy booking if not exists
    if not BookingDetails.objects.filter(awbno=awb).exists():
        BookingDetails.objects.create(
            awbno=awb,
            date=datetime.date.today(),
            sendername="Test Sender",
            senderaddress="123 Sender St, Sender City",
            senderphonenumber="1234567890",
            recievername="Test Receiver",
            recieveraddress="456 Receiver Ave, Receiver City",
            recieverphonenumber="0987654321",
            booked_code="TEST_BRANCH",
            destination_code="TEST_DEST",
            pcs=5,
            wt=Decimal("10.5"),
            mode='Surface',
            contents='Electronics - Laptop and Charger'
        )
        print(f"Created dummy booking {awb}")
    else:
        print(f"Using existing booking {awb}")

    # Test get_booking_data
    data = get_booking_data(awb)
    if data:
        print("Data retrieved successfully:")
        print(data)
    else:
        print("Failed to retrieve data")
        return

    # Test PDF Generation
    try:
        pdf_bytes = generate_booking_pdf(data)
        if pdf_bytes and len(pdf_bytes) > 0:
            print(f"PDF generated successfully. Size: {len(pdf_bytes)} bytes")
            # Save to file for manual inspection
            with open("test_booking.pdf", "wb") as f:
                f.write(pdf_bytes)
            print("Saved to test_booking.pdf")
        else:
            print("PDF generation failed (empty)")
    except Exception as e:
        print(f"PDF generation error: {e}")

    # Test API Endpoint (Mock request)
    factory = RequestFactory()
    request = factory.get(f'/api/booking/pdf/{awb}/')
    response = download_booking_pdf(request, awb=awb)
    
    if response.status_code == 200:
        print("API Endpoint Test Passed (200 OK)")
        print(f"Content-Type: {response['Content-Type']}")
    else:
         print(f"API Endpoint Test Failed: {response.status_code}")

if __name__ == "__main__":
    test_booking_pdf()
