import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="DriverVehicle",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("owner_name", models.CharField(max_length=255, verbose_name="Владелец")),
                ("brand", models.CharField(max_length=100, verbose_name="Марка")),
                ("model", models.CharField(max_length=100, verbose_name="Модель")),
                ("year", models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1900), django.core.validators.MaxValueValidator(2100)], verbose_name="Год выпуска")),
                ("license_plate", models.CharField(max_length=20, verbose_name="Государственный номер")),
                ("vin", models.CharField(max_length=17, verbose_name="VIN-номер")),
                ("insurance_policy", models.CharField(max_length=20, verbose_name="Номер страхового полиса ОСАГО")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Дата обновления")),
                ("driver", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="registered_vehicles", to="users.driverprofile", verbose_name="Водитель")),
            ],
            options={
                "verbose_name": "Автомобиль водителя",
                "verbose_name_plural": "Автомобили водителей",
                "ordering": ["brand", "model"],
            },
        ),
    ]
