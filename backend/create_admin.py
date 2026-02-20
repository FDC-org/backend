
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User
from api.models import UserDetails

username = 'admin'
password = 'admin1234'
email = 'admin@example.com'

try:
    if User.objects.filter(username=username).exists():
        print(f"User '{username}' already exists.")
        user = User.objects.get(username=username)
        user.set_password(password)
        user.is_superuser = True
        user.is_staff = True
        user.save()
        print(f"Updated '{username}' password and permissions.")
    else:
        user = User.objects.create_superuser(username=username, email=email, password=password)
        print(f"Superuser '{username}' created.")

    # Ensure UserDetails exists for this admin so APIs work
    if not UserDetails.objects.filter(user=user).exists():
        UserDetails.objects.create(
            user=user,
            type='ADMIN',
            code='ADMIN001',
            firstname='Super',
            lastname='Admin',
            phone_number='0000000000',
            code_name='System Admin'
        )
        print("Created UserDetails for Admin.")
    else:
        print("UserDetails for Admin already exists.")

except Exception as e:
    print(f"Error: {e}")
