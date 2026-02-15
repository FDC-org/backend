import os
import sys
import django

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.utils.pdf_generator import get_drs_data, generate_error_pdf, generate_drs_pdf
from api.models import DRS

def test_full_flow():
    print("Testing generate_error_pdf...")
    try:
        error_pdf = generate_error_pdf("Test Error Message")
        if error_pdf and len(error_pdf) > 0:
            print(f"Success: Error PDF generated ({len(error_pdf)} bytes)")
            with open('test_error.pdf', 'wb') as f:
                f.write(error_pdf)
        else:
            print("Failed: generate_error_pdf returned empty/None")
    except Exception as e:
        print(f"Exception in generate_error_pdf: {e}")

    print("\nTesting get_drs_data...")
    # Try to find a recent DRS
    drs = DRS.objects.last()
    if not drs:
        print("No DRS found in database to test")
        return

    print(f"Testing with DRS: {drs.drsno}")
    
    try:
        drs_data = get_drs_data(drs.drsno)
        if drs_data:
            print("Success: DRS Data retrieved")
            print(f"Keys: {drs_data.keys()}")
            
            # Now test generating PDF with this data
            print("\nGenerating PDF from retrieved data...")
            pdf_bytes = generate_drs_pdf(drs_data)
            if pdf_bytes:
                print(f"Success: PDF generated ({len(pdf_bytes)} bytes)")
                with open(f'test_drs_{drs.drsno}.pdf', 'wb') as f:
                    f.write(pdf_bytes)
            else:
                print("Failed: generate_drs_pdf returned empty/None")
        else:
            print("Failed: get_drs_data returned None")
    except Exception as e:
        print(f"Exception during data gathering/generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_full_flow()
