import datetime
import time
import uuid
from xmlrpc.client import DateTime

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
    manifestnumber = models.CharField(max_length=20,default=timezone.now().strftime('%y')+ "0" + str(code) + "010001")
    drs_number = models.CharField(max_length=20,default=timezone.now().strftime('%y')+ "0" + str(code) + "020001")

    def fullname(self):
        return str(self.firstname) + " " + str(self.lastname)

    def set_manifest_number(self):
        return timezone.now().strftime('%y')+ "0" + str(self.code) + "010001"

    def set_delivery_number(self):
        return timezone.now().strftime('%y') +"0" + str(self.code) + "020001"



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
    hub = models.CharField(max_length=20)


class DeliveryBoyDetalis(models.Model):
    boy_code = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=20)
    address = models.TextField()
    phone_number = models.CharField(max_length=10)
    code = models.CharField(max_length=20)

class DRS(models.Model):
    drsno = models.CharField(max_length=30, primary_key=True)
    boycode = models.CharField(max_length=20)
    code = models.CharField(max_length=20)
    date= models.DateTimeField()
    location = models.CharField(max_length=20)


class DrsDetails(models.Model):
    drsno = models.CharField(max_length=30)
    awbno = models.CharField(max_length=10)
    status = models.BooleanField(default=False) # status if true either delivered or undeliverd or rto

class DeliveryDetails(models.Model):
    awbno = models.CharField(max_length=10)
    status = models.CharField(max_length=20) #m delivered, undelivered, rto
    recievername = models.CharField(max_length=20,default='')
    recievernumber = models.CharField(max_length=10,default='')
    image = models.ImageField(upload_to='delivery/', null=True, blank=True)
    reason = models.TextField(default="") # it is reason for undelivered
    date = models.DateField()

class Pincodes(models.Model):
    code = models.CharField(max_length=20)
    pincode = models.CharField(max_length=6)


class Locations(models.Model):
    code = models.CharField(max_length=20)
    location = models.CharField(max_length=20)
    location_code = models.CharField(max_length=20)


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
    vehicle_number = models.ForeignKey(Vehicle_Details, on_delete=models.CASCADE, related_name='Vehicle_number',null=True,blank=True)


class OutscanModel(models.Model):
    awbno = models.CharField(max_length=10)
    manifestnumber = models.ForeignKey(ManifestDetails, on_delete=models.CASCADE)


class BookingDetails_temp(models.Model):
    awbno = models.CharField(max_length=10)
    doc_type = models.CharField(max_length=10)
    pcs = models.IntegerField()
    wt = models.DecimalField(decimal_places=2, max_digits=5)

class deliverdordrs(models.Model):
    awbno = models.CharField(max_length=10)


class BookingDetails(models.Model):
    awbno = models.CharField(max_length=10)
    doc_type = models.CharField(max_length=10,blank=True)
    pcs = models.IntegerField(blank=True)
    wt = models.DecimalField(decimal_places=3, max_digits=5,blank=True)
    sendername = models.CharField(max_length=50,blank=True)
    senderaddress = models.TextField(blank=True)
    senderphonenumber = models.CharField(max_length=10,blank=True)
    recievername = models.CharField(max_length=50,blank=True)
    recieveraddress = models.TextField(blank=True)
    recieverphonenumber = models.CharField(max_length=10,blank=True)
    destination_code = models.CharField(max_length=50,blank=True)
    mode = models.CharField(max_length=20,blank=True)
    date = models.DateTimeField(blank=True)
    booked_code = models.CharField(max_length=20,blank=True)
    contents = models.TextField(blank=True)
    pincode = models.CharField(max_length=10,blank=True)


# -------------------- ADMIN REGISTRATION --------------------

from django.contrib import admin


@admin.register(CustomTokenModel)
class CustomTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'created_at', 'expired_at')
    search_fields = ('user__username',)
    readonly_fields = ('token', 'created_at', 'expired_at')


@admin.register(UserDetails)
class UserDetailsAdmin(admin.ModelAdmin):
    list_display = ('user', 'firstname', 'lastname', 'phone_number', 'code', 'type')
    search_fields = ('firstname', 'lastname', 'phone_number', 'code')


@admin.register(HubDetails)
class HubDetailsAdmin(admin.ModelAdmin):
    list_display = ('hub_code', 'hubname', 'location', 'pincode')
    search_fields = ('hub_code', 'hubname')


@admin.register(BranchDetails)
class BranchDetailsAdmin(admin.ModelAdmin):
    list_display = ('branch_code', 'branchname', 'location', 'hub')
    search_fields = ('branch_code', 'branchname')


@admin.register(DeliveryBoyDetalis)
class DeliveryBoyAdmin(admin.ModelAdmin):
    list_display = ('boy_code', 'name', 'phone_number', 'code')
    search_fields = ('boy_code', 'name')


@admin.register(DRS)
class DRSAdmin(admin.ModelAdmin):
    list_display = ('drsno', 'boycode', 'code', 'date', 'location')
    list_filter = ('code', 'date')
    search_fields = ('drsno',)


@admin.register(DrsDetails)
class DrsDetailsAdmin(admin.ModelAdmin):
    list_display = ('drsno', 'awbno', 'status')
    list_filter = ('status',)


@admin.register(DeliveryDetails)
class DeliveryDetailsAdmin(admin.ModelAdmin):
    list_display = ('awbno', 'status', 'recievername')
    list_filter = ('status',)
    search_fields = ('awbno',)


@admin.register(Pincodes)
class PincodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'pincode')
    search_fields = ('pincode',)


@admin.register(Locations)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('code', 'location')
    search_fields = ('location',)


@admin.register(InscanModel)
class InscanAdmin(admin.ModelAdmin):
    list_display = ('awbno', 'date', 'inscaned_branch_code')
    list_filter = ('date',)
    search_fields = ('awbno',)


@admin.register(Vehicle_Details)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('vehiclenumber', 'hub_code')
    search_fields = ('vehiclenumber',)


@admin.register(ManifestDetails)
class ManifestAdmin(admin.ModelAdmin):
    list_display = ('manifestnumber', 'date', 'inscaned_branch_code', 'tohub_branch_code')
    list_filter = ('date',)
    search_fields = ('manifestnumber',)


@admin.register(OutscanModel)
class OutscanAdmin(admin.ModelAdmin):
    list_display = ('awbno', 'manifestnumber')
    search_fields = ('awbno',)


@admin.register(BookingDetails_temp)
class BookingTempAdmin(admin.ModelAdmin):
    list_display = ('awbno', 'doc_type', 'pcs', 'wt')
    search_fields = ('awbno',)


@admin.register(deliverdordrs)
class DeliveredOrDrsAdmin(admin.ModelAdmin):
    list_display = ('awbno',)
    search_fields = ('awbno',)
