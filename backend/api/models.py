import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from .views.utils import token_expiry


# Create your models here.

class CustomTokenModel(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='custom_token')
    created_at = models.DateTimeField(auto_now_add=True)
    expired_at = models.DateTimeField(default=token_expiry)

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

    def fullname(self):
        return str(self.firstname) + " " + str(self.lastname)



class HubDetails(models.Model):
    hub_code = models.CharField(primary_key=True, max_length=20)
    location = models.CharField(max_length=20)
    hubname = models.CharField(max_length=30)
    # pincode = models.CharField(max_length=6)
    address = models.TextField()
    phone_number = models.CharField(max_length=10)
    incharge_name = models.CharField(max_length=20)
    state = models.CharField(max_length=20)
    region = models.CharField(max_length=20)


class BranchDetails(models.Model):
    branch_code = models.CharField(max_length=10, primary_key=True)
    location = models.CharField(max_length=20)
    branchname = models.CharField(max_length=30)
    # pincode = models.CharField(max_length=6)
    address = models.TextField()
    phone_number = models.CharField(max_length=10)
    hub = models.CharField(max_length=20)
    incharge_name = models.CharField(max_length=20)
    manifest_counter = models.CharField(max_length=4, default='001')
    drs_counter = models.CharField(max_length=4, default='001')


class DeliveryBoyDetalis(models.Model):
    boy_code = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    phone_number = models.CharField(max_length=10)
    code = models.CharField(max_length=20)

class DRS(models.Model):
    drsno = models.CharField(max_length=30, primary_key=True)
    boycode = models.CharField(max_length=20)
    code = models.CharField(max_length=20)
    date= models.DateTimeField()
    location = models.CharField(max_length=20)
    document_url = models.URLField(blank=True, null=True)  # Cloudinary PDF URL


class DrsDetails(models.Model):
    drsno = models.CharField(max_length=30)
    awbno = models.CharField(max_length=10)
    status = models.BooleanField(default=False) # status if true either delivered or undeliverd or rto

class DeliveryDetails(models.Model):
    awbno = models.CharField(max_length=10)
    status = models.CharField(max_length=20) #m delivered, undelivered, rto
    recievername = models.CharField(max_length=20,default='')
    recievernumber = models.CharField(max_length=10,default='')
    image = models.TextField(blank=True)
    reason = models.TextField(default="") # it is reason for undelivered
    date = models.DateField()

class Pincodes(models.Model):
    code = models.CharField(max_length=20)
    pincode = models.CharField(max_length=6)
    pincode_type = models.CharField(max_length=20)


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
    doc_type = models.CharField(max_length=10)
    pcs = models.IntegerField()
    wt = models.DecimalField(decimal_places=3, max_digits=5)
    sendername = models.CharField(max_length=50,blank=True)
    senderaddress = models.TextField(blank=True)
    senderphonenumber = models.CharField(max_length=10,blank=True)
    recievername = models.CharField(max_length=50,blank=True)
    recieveraddress = models.TextField(blank=True)
    recieverphonenumber = models.CharField(max_length=10,blank=True)
    destination_code = models.CharField(max_length=50)
    mode = models.CharField(max_length=20,blank=True)
    date = models.DateField()
    booked_code = models.CharField(max_length=20)
    contents = models.TextField(blank=True)
    pincode = models.CharField(max_length=10,blank=True)
    refernce_no = models.CharField(max_length=20,default="")
    eway_bill_no = models.CharField(max_length=50, blank=True, default="")
    invoice_no = models.CharField(max_length=50, blank=True, default="")
    invoice_date = models.DateField(null=True, blank=True)
    invoice_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    booking_type = models.CharField(max_length=20, default="retail")
    client_code = models.CharField(max_length=20, blank=True, default="")
    courier_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    gst = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    packing_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    freight_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    others = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

class ChildPieceDetails(models.Model):
    awbno = models.CharField(max_length=10)
    child_no = models.CharField(max_length=10,unique=True)


class Client(models.Model):
    client_code = models.CharField(primary_key=True, max_length=20)
    name = models.CharField(max_length=100)
    address = models.TextField()
    phone_number = models.CharField(max_length=10)
    code = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.name} ({self.client_code})"


class AppRelease(models.Model):
    version = models.CharField(max_length=20)
    remarks = models.TextField(blank=True)
    build = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    file_id = models.TextField()
    class Meta:
        ordering = ['-created_at']


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
    list_display = ('hub_code', 'hubname', 'location')
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


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('client_code', 'name', 'phone_number', 'code')
    search_fields = ('client_code', 'name', 'code')
