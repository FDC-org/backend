"""
Company Profile Setup Script
This script helps you create company profiles and assign users to companies.
Run this from Django shell: python manage.py shell < setup_companies.py
"""

from api.models import CompanyProfile, UserDetails
from django.contrib.auth.models import User

def create_company(company_code, company_name, logo_url=None, primary_color='#1976d2', secondary_color='#424242'):
    """Create a new company profile"""
    company, created = CompanyProfile.objects.get_or_create(
        company_code=company_code,
        defaults={
            'company_name': company_name,
            'logo_url': logo_url,
            'primary_color': primary_color,
            'secondary_color': secondary_color,
            'is_active': True
        }
    )
    if created:
        print(f"✓ Created company: {company_name} ({company_code})")
    else:
        print(f"⚠ Company already exists: {company_name} ({company_code})")
    return company


def assign_users_to_company(company_code, user_codes=None):
    """Assign users to a company based on their code"""
    try:
        company = CompanyProfile.objects.get(company_code=company_code)
        
        if user_codes:
            # Assign specific users by code
            users = UserDetails.objects.filter(code__in=user_codes)
        else:
            # Assign all users with matching code prefix
            users = UserDetails.objects.filter(code__startswith=company_code)
        
        count = 0
        for user_detail in users:
            user_detail.company = company
            user_detail.save()
            count += 1
            print(f"  ✓ Assigned user: {user_detail.fullname()} ({user_detail.code})")
        
        print(f"✓ Assigned {count} users to {company.company_name}")
        return count
    except CompanyProfile.DoesNotExist:
        print(f"✗ Company not found: {company_code}")
        return 0


# Example usage:
if __name__ == "__main__":
    print("=" * 60)
    print("Company Profile Setup")
    print("=" * 60)
    
    # Example 1: Create Company A
    company_a = create_company(
        company_code='COMP001',
        company_name='Fast Delivery Company',
        logo_url='https://res.cloudinary.com/your-cloud/image/upload/v1/company_logos/comp001.png',
        primary_color='#2196F3',
        secondary_color='#1976D2'
    )
    
    # Example 2: Create Company B
    company_b = create_company(
        company_code='COMP002',
        company_name='Express Courier Services',
        logo_url='https://res.cloudinary.com/your-cloud/image/upload/v1/company_logos/comp002.png',
        primary_color='#4CAF50',
        secondary_color='#388E3C'
    )
    
    print("\n" + "=" * 60)
    print("Assigning Users to Companies")
    print("=" * 60)
    
    # Assign users to companies
    # Option 1: Assign by code prefix (automatic)
    # assign_users_to_company('COMP001')
    
    # Option 2: Assign specific users by their codes
    # assign_users_to_company('COMP001', user_codes=['HUB001', 'BR001', 'BR002'])
    # assign_users_to_company('COMP002', user_codes=['HUB002', 'BR003'])
    
    print("\n" + "=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Update the company codes and names above")
    print("2. Upload logos via API: POST /api/company/logo/")
    print("3. Assign users to companies using the functions above")
    print("4. Test login to see company branding")
