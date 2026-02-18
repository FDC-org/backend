import os
import sys
import django

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.utils.pdf_generator import get_drs_data, generate_drs_pdf
from api.models import DRS

def test_drs_pdf():
    print("Testing DRS PDF generation...")
    
    # Find a DRS that has bookings with pcs or wt > 0
    from api.models import DrsDetails, BookingDetails
    drs_found = None
    
    # Get recent DRSs
    recent_drs = DRS.objects.all().order_by('-date')[:20]
    
    for d in recent_drs:
        details = DrsDetails.objects.filter(drsno=d.drsno)
        for det in details:
            book = BookingDetails.objects.filter(awbno=det.awbno).first()
            if book and (book.pcs > 0 or book.wt > 0):
                drs_found = d
                break
        if drs_found:
            break
            
    if not drs_found:
        print("No suitable DRS found with non-zero pcs/wt, using last DRS")
        drs = DRS.objects.last()
    else:
        drs = drs_found

    if not drs:
        print("No DRS found in database to test")
        return

    print(f"Testing with DRS: {drs.drsno}")
    
    try:
        drs_data = get_drs_data(drs.drsno)
        if drs_data:
            print("Success: DRS Data retrieved")
            print(f"Keys: {drs_data.keys()}")
            print(f"AWB Count: {len(drs_data['awb_items'])}")
            
            # Print first AWB item details
            if drs_data['awb_items']:
                # Inject dummy data for testing
                print("Injecting dummy test data: Pcs=5, Wt=2.5")
                drs_data['awb_items'][0]['pieces'] = 5
                drs_data['awb_items'][0]['weight'] = 2.5
                
                first_item = drs_data['awb_items'][0]
                print(f"First AWB: {first_item['awb_number']}")
                print(f"  Center: {first_item['center']}")
                print(f"  STD: {first_item['doc_type']}")
                print(f"  Pcs: {first_item['pieces']}")
                print(f"  Wt: {first_item['weight']}")
            
            # Now test generating PDF with this data
            print("\nGenerating PDF from retrieved data...")
            pdf_bytes = generate_drs_pdf(drs_data)
            if pdf_bytes:
                print(f"Success: PDF generated ({len(pdf_bytes)} bytes)")
                filename = f'test_drs_{drs.drsno}.pdf'
                with open(filename, 'wb') as f:
                    f.write(pdf_bytes)
                print(f"PDF saved as: {filename}")
            else:
                print("Failed: generate_drs_pdf returned empty/None")
        else:
            print("Failed: get_drs_data returned None")
    except Exception as e:
        print(f"Exception during data gathering/generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_drs_pdf()
