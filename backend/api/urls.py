from django.urls import path
from .views import views
from .views import user
from .views import basic_api_views
from .views import inscan,outscan

urlpatterns = [
    # user api
    path('login/', user.Login.as_view()),
    path('d/', views.Dashboard.as_view()),
    path('csrf/', user.csrf_token),

    # basic api
    path('userdetails/', basic_api_views.UseDetails.as_view()),
    path('bookingdetails/', basic_api_views.GetBookingDetails.as_view()),
    path('addbookingdetails/', basic_api_views.AddBookingDetails.as_view()),
    path('getmanifestnumber/', basic_api_views.GetManifestNumber.as_view()),
    path('vehicledetails/', basic_api_views.VehicleDetails.as_view()),
    path('gethublist/', basic_api_views.GetHubList.as_view()),


    # inscan
    path('inscan/', inscan.Inscan.as_view()),
    path('inscan/<slug:date>', inscan.Inscan.as_view()),

    # outscan
    path('outscan/<slug:date>', outscan.OutScan.as_view()),
    path('outscan/', outscan.OutScan.as_view()),
    path('manifestdata/<slug:manifest_number>',outscan.ManifestData.as_view()),

    path('test/', user.test)
]
