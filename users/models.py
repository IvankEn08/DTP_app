from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class DriverProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="driver_profile")
    full_name = models.CharField("ФИО", max_length=255)
    phone = models.CharField("Телефон", max_length=30)
    driver_license_number = models.CharField("Номер водительского удостоверения", max_length=50, unique=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    class Meta:
        verbose_name = "Профиль водителя"
        verbose_name_plural = "Профили водителей"
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name} ({self.user.username})"


class DriverVehicle(models.Model):
    driver = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name="registered_vehicles", verbose_name="Водитель")
    owner_name = models.CharField("Владелец", max_length=255)
    brand = models.CharField("Марка", max_length=100)
    model = models.CharField("Модель", max_length=100)
    year = models.PositiveIntegerField("Год выпуска", validators=[MinValueValidator(1900), MaxValueValidator(2100)])
    license_plate = models.CharField("Государственный номер", max_length=20)
    vin = models.CharField("VIN-номер", max_length=17)
    insurance_policy = models.CharField("Номер страхового полиса ОСАГО", max_length=20)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    class Meta:
        verbose_name = "Автомобиль водителя"
        verbose_name_plural = "Автомобили водителей"
        ordering = ["brand", "model"]

    def __str__(self):
        return f"{self.brand} {self.model} ({self.license_plate})"
