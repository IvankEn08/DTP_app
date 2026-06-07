import secrets
import string

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def generate_code(existing):
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(secrets.choice(alphabet) for _ in range(8))
        if code not in existing:
            existing.add(code)
            return code


def fill_existing_data(apps, schema_editor):
    Accident = apps.get_model("accidents", "Accident")
    Vehicle = apps.get_model("accidents", "Vehicle")
    existing_codes = set(Accident.objects.exclude(driver_join_code__isnull=True).values_list("driver_join_code", flat=True))
    for accident in Accident.objects.filter(driver_join_code__isnull=True):
        accident.driver_join_code = generate_code(existing_codes)
        accident.save(update_fields=["driver_join_code"])
    for vehicle in Vehicle.objects.filter(owner_name="").select_related("owner"):
        vehicle.owner_name = vehicle.owner.full_name
        vehicle.save(update_fields=["owner_name"])


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("users", "0002_drivervehicle"),
        ("accidents", "0002_sync_legacy_schema"),
    ]

    operations = [
        migrations.AddField(
            model_name="accident",
            name="driver_join_code",
            field=models.CharField(blank=True, max_length=8, null=True, unique=True, verbose_name="Код присоединения второго водителя"),
        ),
        migrations.AddField(
            model_name="accident",
            name="second_driver_role",
            field=models.CharField(choices=[("responsible", "Виновник"), ("victim", "Пострадавший")], default="responsible", max_length=20, verbose_name="Роль второго водителя по коду"),
        ),
        migrations.AddField(
            model_name="vehicle",
            name="owner_name",
            field=models.CharField(blank=True, max_length=255, verbose_name="Владелец"),
        ),
        migrations.AlterField(
            model_name="vehicle",
            name="owner",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="accident_vehicles", to="users.driverprofile", verbose_name="Водитель"),
        ),
        migrations.RunPython(fill_existing_data, migrations.RunPython.noop),
    ]
