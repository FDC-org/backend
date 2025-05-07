import datetime
import time
import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


# Create your models here.

class CustomTokenModel(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='custom_token')
    created_at = models.DateTimeField(auto_now_add=True)
    expired_at = models.DateTimeField(default=timezone.now() + datetime.timedelta(days=5))

    def is_expired(self):
        return timezone.now() >= self.expired_at


class UserDetails(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='users')
    type = models.CharField(max_length=10)
    code = models.CharField(max_length=10)
    firstname = models.CharField(max_length=100)
    lastname = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=10)
    code_name = models.CharField(max_length=30)
    manifestnumber = models.CharField(max_length=20)

    def fullname(self):
        return str(self.firstname) + " " + str(self.lastname)

    def set_manifest_number(self):
        return "250" + str(self.code) + "010001"



class HubDetails(models.Model):
    hub_code = models.CharField(primary_key=True, max_length=20)
    location = models.CharField(max_length=20)
    hubname = models.CharField(max_length=30)
    pincode = models.CharField(max_length=6)
    address = models.TextField()
    phone_number = models.CharField(max_length=10)


class BranchDetails(models.Model):
    branch_code = models.CharField(max_length=10, primary_key=True)
    location = models.CharField(max_length=20)
    branchname = models.CharField(max_length=30)
    pincode = models.CharField(max_length=6)
    address = models.TextField()
    phone_number = models.CharField(max_length=10)
    hub = models.OneToOneField(HubDetails, on_delete=models.CASCADE, related_name='LinkedHub')


class DeliveryBoyDetalis(models.Model):
    boy_code = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=20)
    address = models.TextField()
    phone_number = models.CharField(max_length=10)
    branch = models.OneToOneField(BranchDetails, on_delete=models.CASCADE, related_name='LinkedBranch_del')


class Pincodes(models.Model):
    branch_code = models.OneToOneField(BranchDetails, related_name='LinkedBranch_pincodes', on_delete=models.CASCADE)
    pincode = models.CharField(max_length=6)


class Locations(models.Model):
    branch_code = models.OneToOneField(BranchDetails, related_name='LinkedBranch_location', on_delete=models.CASCADE)
    location = models.CharField(max_length=20)


class InscanModel(models.Model):
    date = models.DateTimeField()
    awbno = models.CharField(max_length=10)
    inscaned_branch_code = models.CharField(max_length=10)


class Vehicle_Details(models.Model):
    hub_code = models.CharField(max_length=20)
    vehiclenumber = models.CharField(max_length=10, unique=True)


class ManifestDetails(models.Model):
    date = models.DateTimeField()
    inscaned_branch_code = models.CharField(max_length=10)
    tohub_branch_code = models.CharField(max_length=10)
    manifestnumber = models.CharField(max_length=30, unique=True)
    vehicle_number = models.ForeignKey(Vehicle_Details, on_delete=models.CASCADE)


class OutscanModel(models.Model):
    awbno = models.CharField(max_length=10)
    manifestnumber = models.ForeignKey(ManifestDetails, on_delete=models.CASCADE)


class BookingDetails_temp(models.Model):
    awbno = models.CharField(max_length=10)
    doc_type = models.CharField(max_length=10)
    pcs = models.IntegerField()
    wt = models.DecimalField(decimal_places=2, max_digits=5)
