from django.urls import path
from . import views

urlpatterns = [
    path("devices/", views.device_list, name="device_list"),
    path("devices/register/", views.register_device, name="register_device"),
    path("api/data/", views.receive_data, name="receive_data"),
    path("latest/", views.latest_readings),
]