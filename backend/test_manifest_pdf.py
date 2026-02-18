import os
import sys
import django

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.utils.pdf_generator import get_manifest_data, generate_manifest_pdf, generate_error_pdf
from api.models import ManifestDetails

def test_manifest_pdf():
    print("Testing Manifest PDF generation...")
    
    # Try to find a recent Manifest
    manifest = ManifestDetails.objects.last()
    if not manifest:
        print("No Manifest found in database to test")
        return

    print(f"Testing with Manifest: {manifest.manifestnumber}")
    
    try:
        manifest_data = get_manifest_data(manifest.manifestnumber)
        if manifest_data:
            print("Success: Manifest Data retrieved")
            print(f"Keys: {manifest_data.keys()}")
            print(f"Origin: {manifest_data['origin']}")
            print(f"Destination: {manifest_data['destination']}")
            print(f"Vehicle: {manifest_data.get('vehicle_number', 'N/A')}")
            print(f"AWB Count: {len(manifest_data['awb_list'])}")
            
            print("\nAWB Details:")
            for awb in manifest_data['awb_list']:
                print(f"  - AWB: {awb['awb_number']}, Dest Code: {awb.get('destination', 'N/A')}, Sender: {awb.get('sender', 'N/A')}")
            
            # Now test generating PDF with this data
            print("\nGenerating PDF from retrieved data...")
            pdf_bytes = generate_manifest_pdf(manifest_data)
            if pdf_bytes:
                print(f"Success: PDF generated ({len(pdf_bytes)} bytes)")
                with open(f'test_manifest_{manifest.manifestnumber}.pdf', 'wb') as f:
                    f.write(pdf_bytes)
                print(f"PDF saved as: test_manifest_{manifest.manifestnumber}.pdf")
            else:
                print("Failed: generate_manifest_pdf returned empty/None")
        else:
            print("Failed: get_manifest_data returned None")
    except Exception as e:
        print(f"Exception during data gathering/generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_manifest_pdf()
