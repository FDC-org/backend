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

from api.models import BookingDetails, UserDetails, BranchDetails, HubDetails
from api.utils.pdf_generator import generate_booking_pdf, generate_cargo_booking_pdf, get_booking_data
from api.views.booking_pdf import download_booking_pdf

def test_booking_pdf():
    print("Testing Booking PDF Generation...")
    
    # thorough setup of dummy data
    awb = "LR_TEST_1"
    
    # Recreate dummy branch and booking each run
    BranchDetails.objects.filter(branch_code="TEST_BR").delete()
    BranchDetails.objects.create(
        branch_code="TEST_BR",
        location="TEST_LOCATION",
        branchname="TEST BRANCH OFFICE",
        address="123 Branch St, Branch City, State, 123456",
        phone_number="9876543210",
        hub="TEST_HUB",
        incharge_name="Test Incharge"
    )
    
    BranchDetails.objects.filter(branch_code="TEST_DE").delete()
    BranchDetails.objects.create(
        branch_code="TEST_DE",
        location="TEST_DEST_LOCATION",
        branchname="TEST DESTINATION OFFICE",
        address="456 Dest St, Dest City, State, 654321",
        phone_number="8765432109",
        hub="TEST_HUB",
        incharge_name="Dest Incharge"
    )
    
    BookingDetails.objects.filter(awbno=awb).delete()
    
    BookingDetails.objects.create(
        awbno=awb,
        date=datetime.date.today(),
        sendername="Test Sender",
        senderaddress="123 Sender St, Sender City",
        senderphonenumber="1234567890",
        recievername="Test Receiver",
        recieveraddress="456 Receiver Ave, Receiver City",
        recieverphonenumber="0987654321",
        booked_code="TEST_BR",
        destination_code="TEST_DE",
        pcs=5,
        wt=Decimal("10.5"),
        mode='Surface',
        contents='Electronics - Laptop and Charger',
        eway_bill_no="EWAY123456789",
        invoice_no="INV-998877",
        invoice_date=datetime.date.today(),
        invoice_amount=Decimal("25000.00"),
        refernce_no="REF-55",
        courier_charges=Decimal("150.00"),
        gst=Decimal("27.00"),
        packing_charges=Decimal("10.00"),
        freight_charges=Decimal("50.00"),
        others=Decimal("5.00"),
        total=Decimal("242.00")
    )
    print(f"Created dummy booking {awb} and branch details")

    # Test get_booking_data
    data = get_booking_data(awb)
    if data:
        print("Data retrieved successfully:")
        print(data)
    else:
        print("Failed to retrieve data")
        return

    # Test PDF Generation (Parcel)
    try:
        pdf_bytes = generate_booking_pdf(data)
        if pdf_bytes and len(pdf_bytes) > 0:
            print(f"Parcel PDF generated successfully. Size: {len(pdf_bytes)} bytes")
            with open("test_booking_parcel.pdf", "wb") as f:
                f.write(pdf_bytes)
            print("Saved to test_booking_parcel.pdf")
        else:
            print("Parcel PDF generation failed (empty)")
    except Exception as e:
        print(f"Parcel PDF generation error: {e}")

    # Test PDF Generation (Cargo)
    try:
        pdf_bytes_cargo = generate_cargo_booking_pdf(data)
        if pdf_bytes_cargo and len(pdf_bytes_cargo) > 0:
            print(f"Cargo PDF generated successfully. Size: {len(pdf_bytes_cargo)} bytes")
            with open("test_booking_cargo.pdf", "wb") as f:
                f.write(pdf_bytes_cargo)
            print("Saved to test_booking_cargo.pdf")
        else:
            print("Cargo PDF generation failed (empty)")
    except Exception as e:
        print(f"Cargo PDF generation error: {e}")

    # Test API Endpoint - Parcel
    factory = RequestFactory()
    request_parcel = factory.get(f'/api/booking/pdf/{awb}/?type=parcel')
    response_parcel = download_booking_pdf(request_parcel, awb=awb)
    
    if response_parcel.status_code == 200:
        print("API Endpoint Test (Parcel) Passed (200 OK)")
    else:
        print(f"API Endpoint Test (Parcel) Failed: {response_parcel.status_code}")

    # Test API Endpoint - Cargo
    request_cargo = factory.get(f'/api/booking/pdf/{awb}/?type=cargo')
    response_cargo = download_booking_pdf(request_cargo, awb=awb)
    
    if response_cargo.status_code == 200:
        print("API Endpoint Test (Cargo) Passed (200 OK)")
    else:
        print(f"API Endpoint Test (Cargo) Failed: {response_cargo.status_code}")

if __name__ == "__main__":
    test_booking_pdf()
