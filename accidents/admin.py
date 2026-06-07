from django.contrib import admin

from .models import Accident, AccidentDriver, AccidentPhoto, Damage, SubmissionLog, Vehicle, WitnessStatement


class AccidentDriverInline(admin.TabularInline):
    model = AccidentDriver
    extra = 0


class VehicleInline(admin.TabularInline):
    model = Vehicle
    extra = 0


class AccidentPhotoInline(admin.TabularInline):
    model = AccidentPhoto
    extra = 0


@admin.register(Accident)
class AccidentAdmin(admin.ModelAdmin):
    list_display = ("title", "access_code", "driver_join_code", "accident_date", "location", "created_by", "submitted_at")
    search_fields = ("title", "access_code", "driver_join_code", "location", "created_by__username")
    list_filter = ("submitted_at", "created_at", "accident_date")
    inlines = (AccidentDriverInline, VehicleInline, AccidentPhotoInline)


@admin.register(AccidentDriver)
class AccidentDriverAdmin(admin.ModelAdmin):
    list_display = ("accident", "driver", "role", "is_ready", "ready_at", "created_at")
    search_fields = ("accident__title", "accident__access_code", "driver__full_name", "driver__driver_license_number")
    list_filter = ("role", "is_ready", "created_at")


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("brand", "model", "license_plate", "owner", "owner_name", "accident", "insurance_policy")
    search_fields = ("brand", "model", "license_plate", "vin", "insurance_policy", "owner__full_name", "owner_name", "accident__access_code")
    list_filter = ("brand", "created_at")


@admin.register(Damage)
class DamageAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "damage_area", "severity", "created_at")
    search_fields = ("vehicle__license_plate", "damage_area", "description")
    list_filter = ("severity", "created_at")


@admin.register(AccidentPhoto)
class AccidentPhotoAdmin(admin.ModelAdmin):
    list_display = ("accident", "vehicle", "uploaded_by", "description", "created_at")
    search_fields = ("accident__title", "accident__access_code", "description", "uploaded_by__username")
    list_filter = ("created_at",)


@admin.register(WitnessStatement)
class WitnessStatementAdmin(admin.ModelAdmin):
    list_display = ("witness_full_name", "witness_phone", "accident", "created_at")
    search_fields = ("witness_full_name", "witness_phone", "statement_text", "accident__access_code")
    list_filter = ("created_at",)


@admin.register(SubmissionLog)
class SubmissionLogAdmin(admin.ModelAdmin):
    list_display = ("accident", "submitted_by", "submitted_at", "created_at")
    search_fields = ("accident__access_code", "submitted_by__username", "comment")
    list_filter = ("submitted_at", "created_at")
