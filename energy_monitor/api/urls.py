from django.urls import path
from . import views

urlpatterns = [
    # Device Dashboard
    path("", views.device_list, name="device_list"),

    # Device Registration
    path(
        "devices/register/",
        views.register_device,
        name="register_device"
    ),

    # ESP8266 Data Receiving API
    path(
        "api/data/",
        views.receive_data,
        name="receive_data"
    ),

    # Latest Readings API
    path(
        "latest/",
        views.latest_readings,
        name="latest_readings"
    ),

    # Historical Readings API
    path(
        "history/",
        views.historical_readings,
        name="historical_readings"
    ),

    # Edit Device
    path(
        "devices/edit/<int:device_id>/",
        views.edit_device,
        name="edit_device"
    ),

    # Delete Device
    path(
        "devices/delete/<int:device_id>/",
        views.delete_device,
        name="delete_device"
    ),
]