import os
import sys
import django

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models import ManifestDetails, Vehicle_Details

def check_manifest_vehicle():
    print("Checking Manifest vehicle numbers...")
    print("=" * 60)
    
    # Get all manifests
    manifests = ManifestDetails.objects.all()[:10]  # Check last 10
    
    for manifest in manifests:
        print(f"\nManifest: {manifest.manifestnumber}")
        print(f"  Date: {manifest.date}")
        print(f"  Vehicle Number Field: {manifest.vehicle_number}")
        
        if manifest.vehicle_number:
            print(f"  Vehicle Number Value: {manifest.vehicle_number.vehiclenumber}")
        else:
            print(f"  Vehicle Number Value: None (not set)")
    
    print("\n" + "=" * 60)
    print("\nAll Vehicle Details in database:")
    vehicles = Vehicle_Details.objects.all()
    for v in vehicles:
        print(f"  - {v.vehiclenumber} (Hub: {v.hub_code})")

if __name__ == "__main__":
    check_manifest_vehicle()
