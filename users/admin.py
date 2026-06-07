from django.contrib import admin

from .models import DriverProfile, DriverVehicle


@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone", "driver_license_number", "user", "created_at")
    search_fields = ("full_name", "phone", "driver_license_number", "user__username")
    list_filter = ("created_at",)


@admin.register(DriverVehicle)
class DriverVehicleAdmin(admin.ModelAdmin):
    list_display = ("brand", "model", "license_plate", "driver", "owner_name", "insurance_policy")
    search_fields = ("brand", "model", "license_plate", "vin", "insurance_policy", "driver__full_name", "owner_name")
    list_filter = ("brand", "created_at")
