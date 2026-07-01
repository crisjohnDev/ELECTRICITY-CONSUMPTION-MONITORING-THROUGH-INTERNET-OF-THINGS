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

    devices = Device.objects.all()

    return render(
        request,
        "devices/device_list.html",
        {
            "devices": devices
        }
    )

def latest_readings(request):

    readings = EnergyReading.objects.select_related("device").order_by("-created_at")

    data = []

    for reading in readings:

        data.append({
            "device_id": reading.device.device_id,
            "device_name": reading.device.device_name,
            "voltage": reading.voltage,
            "current": reading.current,
            "power": reading.power,
            "energy": reading.energy,
            "pf": reading.pf,
            "peak": reading.peak,
            "time": reading.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        })

    return JsonResponse(data, safe=False)