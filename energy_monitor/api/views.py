from django.shortcuts import render, redirect
from .models import Device

import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Device
from .models import EnergyReading

@csrf_exempt
def receive_data(request):

    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    data = json.loads(request.body)

    try:

        device = Device.objects.get(
            device_id=data["device_id"],
            is_active=True
        )

    except Device.DoesNotExist:

        return JsonResponse({
            "success": False,
            "message": "Device not registered"
        }, status=404)

    EnergyReading.objects.create(
        device=device,
        voltage=data["voltage"],
        current=data["current"],
        power=data["power"],
        energy=data["energy"],
        pf=data["pf"],
        peak=data["peak"],
    )

    return JsonResponse({
        "success": True
    })

def register_device(request):

    if request.method == "POST":

        Device.objects.create(
            device_id=request.POST["device_id"],
            device_name=request.POST["device_name"],
            location=request.POST["location"]
        )

        return redirect("device_list")

    return render(request, "devices/register_device.html")

def device_list(request):
    devices = []

    for device in Device.objects.all():

        latest = (
            EnergyReading.objects
            .filter(device=device)
            .order_by("-created_at")
            .first()
        )

        devices.append({
            "device": device,
            "reading": latest,
        })

    return render(request, "devices/device_list.html", {
        "devices": devices
    })

def latest_readings(request):
    data = []

    for device in Device.objects.all():

        reading = (
            EnergyReading.objects
            .filter(device=device)
            .order_by("-created_at")
            .first()
        )

        if reading:
            data.append({
                "device_id": device.device_id,
                "device_name": device.device_name,
                "voltage": reading.voltage,
                "current": reading.current,
                "power": reading.power,
                "energy": reading.energy,
                "pf": reading.pf,
                "peak": reading.peak,
                "time": reading.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "Online",
            })
        else:
            data.append({
                "device_id": device.device_id,
                "device_name": device.device_name,
                "voltage": None,
                "current": None,
                "power": None,
                "energy": None,
                "pf": None,
                "peak": None,
                "time": None,
                "status": "Offline",
            })

    return JsonResponse(data, safe=False)