import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DriverProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("full_name", models.CharField(max_length=255, verbose_name="ФИО")),
                ("phone", models.CharField(max_length=30, verbose_name="Телефон")),
                ("driver_license_number", models.CharField(max_length=50, unique=True, verbose_name="Номер водительского удостоверения")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Дата обновления")),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="driver_profile", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Профиль водителя",
                "verbose_name_plural": "Профили водителей",
                "ordering": ["full_name"],
            },
        ),
    ]
