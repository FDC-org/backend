import sys
import os

sys.path.append(os.getcwd())

from api.utils.pdf_generator import generate_drs_pdf

# Test case with potential problematic values
drs_data_edge_case = {
    'drs_number': '', # Empty string for barcode?
    'branch_name': None, # None value
    'branch_address': None,
    'date': None,
    'area': 'Test Area (Special Chars: & < >)',
    'delivery_boy': 'Test Boy',
    'awb_items': [
        {
            'center': None,
            'doc_type': 'NON-DOX',
            'awb_number': '', # Empty AWB for barcode
            'party_name': 'Test Party',
            'party_phone': None,
            'pieces': 0,
            'weight': 0.0,
            'remarks': 'Test Remarks'
        }
    ]
}

print("Testing edge cases...")
try:
    # We expect failures or handled errors here
    # ReportLab might fail on None in Paragraph if f-string logic isn't perfect in caller
    # But generate_drs_pdf accesses keys directly.
    # If values are None, f-strings in generate_drs_pdf handle them?
    
    # Check generate_drs_pdf implementation again:
    # branch_info = Paragraph(f'<b>{drs_data["branch_name"]}</b><br/>{drs_data["branch_address"]}', styles['Normal'])
    # f-string with None works -> "None"
    
    pdf_bytes = generate_drs_pdf(drs_data_edge_case)
    with open('test_output_edge.pdf', 'wb') as f:
        f.write(pdf_bytes)
    print("Edge case PDF generated successfully")
except Exception as e:
    print(f"Edge case failed with: {e}")
    import traceback
    traceback.print_exc()
