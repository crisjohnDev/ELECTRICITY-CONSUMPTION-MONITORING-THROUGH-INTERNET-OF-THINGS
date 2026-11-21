import json
import math
from datetime import timedelta

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.db.models import Avg, Max
from django.db.models.functions import TruncMinute, TruncHour, TruncDay

from .models import Device, EnergyReading


# =========================================================
# EDIT DEVICE
# =========================================================

def edit_device(request, device_id):

    try:
        device = Device.objects.get(id=device_id)

    except Device.DoesNotExist:
        return redirect("device_list")

    if request.method == "POST":

        new_device_id = request.POST.get(
            "device_id", ""
        ).strip()

        device_name = request.POST.get(
            "device_name", ""
        ).strip()

        location = request.POST.get(
            "location", ""
        ).strip()

        if not new_device_id or not device_name:

            return render(
                request,
                "devices/edit_device.html",
                {
                    "device": device,
                    "error": "Device ID and device name are required."
                }
            )

        # Check duplicate device ID
        if Device.objects.filter(
            device_id=new_device_id
        ).exclude(id=device.id).exists():

            return render(
                request,
                "devices/edit_device.html",
                {
                    "device": device,
                    "error": "This device ID is already registered."
                }
            )

        # Update device
        device.device_id = new_device_id
        device.device_name = device_name
        device.location = location

        device.save()

        return redirect("device_list")

    return render(
        request,
        "devices/edit_device.html",
        {"device": device}
    )


# =========================================================
# DELETE DEVICE
# =========================================================

def delete_device(request, device_id):

    if request.method != "POST":
        return redirect("device_list")

    try:
        device = Device.objects.get(id=device_id)

    except Device.DoesNotExist:
        return redirect("device_list")

    device.delete()

    return redirect("device_list")



# =========================================================
# RECEIVE ESP8266 DATA
# =========================================================

@csrf_exempt
def receive_data(request):

    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "POST only"},
            status=405
        )

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"success": False, "message": "Invalid JSON data"},
            status=400
        )

    required_fields = [
        "device_id",
        "voltage",
        "current",
        "power",
        "energy",
        "pf",
        "peak",
    ]

    for field in required_fields:
        if field not in data:
            return JsonResponse(
                {
                    "success": False,
                    "message": f"Missing required field: {field}"
                },
                status=400
            )

    # Validate numeric readings
    try:
        voltage = float(data["voltage"])
        current = float(data["current"])
        power = float(data["power"])
        energy = float(data["energy"])
        pf = float(data["pf"])
        peak = float(data["peak"])

        readings = [voltage, current, power, energy, pf, peak]

        if not all(math.isfinite(value) for value in readings):
            raise ValueError("Invalid numeric value")

    except (TypeError, ValueError):
        return JsonResponse(
            {"success": False, "message": "Invalid numeric readings"},
            status=400
        )

    # Find registered active device
    try:
        device = Device.objects.get(
            device_id=data["device_id"],
            is_active=True
        )

    except Device.DoesNotExist:
        return JsonResponse(
            {
                "success": False,
                "message": "Device not registered or inactive"
            },
            status=404
        )

    # Save reading
    EnergyReading.objects.create(
        device=device,
        voltage=voltage,
        current=current,
        power=power,
        energy=energy,
        pf=pf,
        peak=peak,
    )

    return JsonResponse({
        "success": True,
        "message": "Reading saved successfully"
    })


# =========================================================
# REGISTER DEVICE
# =========================================================

def register_device(request):

    if request.method == "POST":

        device_id = request.POST.get("device_id", "").strip()
        device_name = request.POST.get("device_name", "").strip()
        location = request.POST.get("location", "").strip()

        if not device_id or not device_name:
            return render(
                request,
                "devices/register_device.html",
                {"error": "Device ID and device name are required."}
            )

        if Device.objects.filter(device_id=device_id).exists():
            return render(
                request,
                "devices/register_device.html",
                {"error": "This device ID is already registered."}
            )

        Device.objects.create(
            device_id=device_id,
            device_name=device_name,
            location=location
        )

        return redirect("device_list")

    return render(request, "devices/register_device.html")


# =========================================================
# DEVICE LIST
# =========================================================

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

    return render(
        request,
        "devices/device_list.html",
        {"devices": devices}
    )


# =========================================================
# LATEST READINGS API
# =========================================================

def latest_readings(request):

    data = []

    # Consider a device online if it sent data within 2 minutes
    online_threshold = timezone.now() - timedelta(minutes=2)

    for device in Device.objects.all():

        reading = (
            EnergyReading.objects
            .filter(device=device)
            .order_by("-created_at")
            .first()
        )

        if reading:

            is_online = reading.created_at >= online_threshold

            data.append({
                "device_id": device.device_id,
                "device_name": device.device_name,
                "voltage": reading.voltage,
                "current": reading.current,
                "power": reading.power,
                "energy": reading.energy,
                "pf": reading.pf,
                "peak": reading.peak,
                "time": timezone.localtime(
                    reading.created_at
                ).strftime("%Y-%m-%d %H:%M:%S"),
                "status": "Online" if is_online else "Offline",
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


# =========================================================
# HISTORICAL READINGS API
# Supports: minute, hour, day
#
# Example:
# /history/?interval=minute
# /history/?interval=hour
# /history/?interval=day
#
# Optional filters:
# &device_id=ESP001
# &start_date=2026-11-01
# &end_date=2026-11-09
# =========================================================

def historical_readings(request):

    interval = request.GET.get("interval", "minute").lower()

    device_id = request.GET.get("device_id", "").strip()

    start_date = request.GET.get("start_date", "").strip()
    end_date = request.GET.get("end_date", "").strip()

    # Select grouping interval
    interval_functions = {
        "minute": TruncMinute,
        "hour": TruncHour,
        "day": TruncDay,
    }

    if interval not in interval_functions:
        return JsonResponse(
            {
                "success": False,
                "message": "Invalid interval. Use minute, hour, or day."
            },
            status=400
        )

    # Base queryset
    readings = EnergyReading.objects.select_related("device").all()

    # Device filter
    if device_id:

        if not Device.objects.filter(device_id=device_id).exists():
            return JsonResponse(
                {
                    "success": False,
                    "message": "Device not found."
                },
                status=404
            )

        readings = readings.filter(device__device_id=device_id)

    # Start date filter
    if start_date:

        parsed_start = parse_date(start_date)

        if parsed_start is None:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Invalid start_date. Use YYYY-MM-DD."
                },
                status=400
            )

        readings = readings.filter(
            created_at__date__gte=parsed_start
        )

    # End date filter
    if end_date:

        parsed_end = parse_date(end_date)

        if parsed_end is None:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Invalid end_date. Use YYYY-MM-DD."
                },
                status=400
            )

        readings = readings.filter(
            created_at__date__lte=parsed_end
        )

    if start_date and end_date and parsed_start > parsed_end:
        return JsonResponse(
            {
                "success": False,
                "message": "Start date cannot be later than end date."
            },
            status=400
        )

    # Group records by selected time interval
    truncate_function = interval_functions[interval]

    grouped_readings = (
        readings
        .annotate(
            period=truncate_function(
                "created_at",
                tzinfo=timezone.get_current_timezone()
            )
        )
        .values(
            "device__device_id",
            "device__device_name",
            "period"
        )
        .annotate(
            voltage=Avg("voltage"),
            current=Avg("current"),
            power=Avg("power"),
            energy=Max("energy"),
            pf=Avg("pf"),
            peak=Max("peak"),
        )
        .order_by("period", "device__device_name")
    )

    # Prepare JSON response
    data = []

    for item in grouped_readings:

        period = item["period"]

        data.append({
            "device_id": item["device__device_id"],
            "device_name": item["device__device_name"],

            "voltage": round(item["voltage"] or 0, 2),
            "current": round(item["current"] or 0, 3),
            "power": round(item["power"] or 0, 2),

            "energy": round(item["energy"] or 0, 4),

            "pf": round(item["pf"] or 0, 3),
            "peak": round(item["peak"] or 0, 2),

            "time": timezone.localtime(
                period
            ).strftime("%Y-%m-%d %H:%M:%S"),
        })

    return JsonResponse({
        "success": True,
        "interval": interval,
        "count": len(data),
        "data": data
    })