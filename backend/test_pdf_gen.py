import sys
import os

# Add the current directory to sys.path so we can import api
sys.path.append(os.getcwd())

from api.utils.pdf_generator import generate_drs_pdf

drs_data = {
    'drs_number': '26598268260801017',
    'branch_name': 'Test Branch',
    'branch_address': '123 Test St, Test City',
    'date': '15/02/2026 12:00:00',
    'area': 'Test Area',
    'delivery_boy': 'Test Boy',
    'awb_items': [
        {
            'center': 'Test Center',
            'doc_type': 'NON-DOX',
            'awb_number': '1234567890',
            'party_name': 'Test Party',
            'party_phone': '1234567890',
            'pieces': 1,
            'weight': 1.0,
            'remarks': 'Test Remarks'
        }
    ]
}

try:
    print("Attempting to generate PDF...")
    pdf_bytes = generate_drs_pdf(drs_data)
    with open('test_output.pdf', 'wb') as f:
        f.write(pdf_bytes)
    print(f"PDF generated successfully, size: {len(pdf_bytes)} bytes")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
