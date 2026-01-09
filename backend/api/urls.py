from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from .views import views, delivery,user,basic_api_views,inscan,outscan
from .views.Booking import Booking
from .views.delivery import DRSapi, Delivered

urlpatterns = [
    # user api
    path('login/', user.Login.as_view()),
    path('d/', views.Dashboard.as_view()),
    path('csrf/', user.csrf_token),
    path('getversion/',basic_api_views.VersionAPI.as_view()),

    # basic api
    path('userdetails/', basic_api_views.UseDetails.as_view()),
    path('bookingdetails/', basic_api_views.GetBookingDetails.as_view()),
    path('addbookingdetails/', basic_api_views.AddBookingDetails.as_view()),
    path('getmanifestnumber/', basic_api_views.GetManifestNumber.as_view()),
    path('vehicledetails/', basic_api_views.VehicleDetails.as_view()),
    path('gethublist/', basic_api_views.GetHubList.as_view()),
    path('verify_token/', basic_api_views.VerifyToken.as_view()),
    path('track/<slug:awbno>', basic_api_views.Track.as_view()),
    path('get_boy_loc/',delivery.getDeliveryBoys_locations.as_view()),

    # booking

    path('booking/',Booking.as_view()),


    # inscan
    path('inscan/', inscan.Inscan.as_view()),
    path('inscanmobile/', inscan.InscanMobile.as_view()),
    path('inscan/<slug:date>', inscan.Inscan.as_view()),

    # outscan
    path('outscan/<slug:date>', outscan.OutScan.as_view()),
    path('outscan/', outscan.OutScan.as_view()),
    path('outscanmobile/', outscan.OutScanMobile.as_view()),
    path('manifestdata/<slug:manifest_number>', outscan.ManifestData.as_view()),

    path('drs/<slug:date>',DRSapi.as_view()),
    path('drs/', DRSapi.as_view()),
    path('delivery/',Delivered.as_view()),

    path('test/', user.test),
    path('adddelboy/',delivery.AddDeliveryBoys.as_view()),
    path('addloc/',delivery.AddAreas.as_view()),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)