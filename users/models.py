from django.conf import settings
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
