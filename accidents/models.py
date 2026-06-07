import secrets
import string

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from users.models import DriverProfile


def generate_unique_code(field_name):
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(secrets.choice(alphabet) for _ in range(8))
        if not Accident.objects.filter(**{field_name: code}).exists():
            return code


def generate_access_code():
    return generate_unique_code("access_code")


def generate_driver_join_code():
    return generate_unique_code("driver_join_code")


class Accident(models.Model):
    SECOND_DRIVER_ROLE_CHOICES = (
        ("responsible", "Виновник"),
        ("victim", "Пострадавший"),
    )

    title = models.CharField("Краткое название происшествия", max_length=255)
    accident_date = models.DateTimeField("Дата и время ДТП")
    location = models.CharField("Место происшествия", max_length=255)
    access_code = models.CharField("Код доступа для свидетелей", max_length=8, unique=True, blank=True)
    driver_join_code = models.CharField("Код присоединения второго водителя", max_length=8, unique=True, blank=True, null=True)
    second_driver_role = models.CharField("Роль второго водителя по коду", max_length=20, choices=SECOND_DRIVER_ROLE_CHOICES, default="responsible")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_accidents", verbose_name="Создатель")
    submitted_at = models.DateTimeField("Дата и время отправки в ГИБДД", null=True, blank=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    class Meta:
        verbose_name = "ДТП"
        verbose_name_plural = "ДТП"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.access_code:
            self.access_code = generate_access_code()
        if not self.driver_join_code:
            self.driver_join_code = generate_driver_join_code()
        super().save(*args, **kwargs)

    @property
    def is_submitted(self):
        return self.submitted_at is not None

    def __str__(self):
        return f"{self.title} — {self.access_code}"


class AccidentDriver(models.Model):
    class Role(models.TextChoices):
        RESPONSIBLE = "responsible", "Виновник"
        VICTIM = "victim", "Пострадавший"

    accident = models.ForeignKey(Accident, on_delete=models.CASCADE, related_name="drivers", verbose_name="ДТП")
    driver = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name="accident_roles", verbose_name="Водитель")
    role = models.CharField("Роль в ДТП", max_length=20, choices=Role.choices)
    comment = models.TextField("Комментарий водителя", blank=True)
    is_ready = models.BooleanField("Водитель подтвердил заполнение", default=False)
    ready_at = models.DateTimeField("Дата подтверждения заполнения", null=True, blank=True)
    created_at = models.DateTimeField("Дата добавления", auto_now_add=True)

    class Meta:
        verbose_name = "Водитель-участник ДТП"
        verbose_name_plural = "Водители-участники ДТП"
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(fields=["accident", "driver"], name="unique_accident_driver")
        ]

    def __str__(self):
        return f"{self.driver.full_name} — {self.accident.title}"


class Vehicle(models.Model):
    accident = models.ForeignKey(Accident, on_delete=models.CASCADE, related_name="vehicles", verbose_name="ДТП")
    owner = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name="accident_vehicles", verbose_name="Водитель")
    owner_name = models.CharField("Владелец", max_length=255, blank=True)
    brand = models.CharField("Марка", max_length=100)
    model = models.CharField("Модель", max_length=100)
    year = models.PositiveIntegerField("Год выпуска", validators=[MinValueValidator(1900), MaxValueValidator(2100)])
    license_plate = models.CharField("Государственный номер", max_length=20)
    vin = models.CharField("VIN-номер", max_length=17)
    insurance_policy = models.CharField("Номер страхового полиса ОСАГО", max_length=20)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    class Meta:
        verbose_name = "Транспортное средство"
        verbose_name_plural = "Транспортные средства"
        ordering = ["brand", "model"]

    def __str__(self):
        return f"{self.brand} {self.model} ({self.license_plate})"

    @property
    def display_owner_name(self):
        return self.owner_name or self.owner.full_name


class Damage(models.Model):
    class Severity(models.TextChoices):
        MINOR = "minor", "Незначительное"
        MEDIUM = "medium", "Среднее"
        SERIOUS = "serious", "Серьёзное"

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="damages", verbose_name="Автомобиль")
    damage_area = models.CharField("Область повреждения", max_length=150)
    description = models.TextField("Описание повреждения")
    severity = models.CharField("Степень повреждения", max_length=20, choices=Severity.choices)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    class Meta:
        verbose_name = "Повреждение"
        verbose_name_plural = "Повреждения"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.vehicle} — {self.damage_area}"


class AccidentPhoto(models.Model):
    accident = models.ForeignKey(Accident, on_delete=models.CASCADE, related_name="photos", verbose_name="ДТП")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name="photos", verbose_name="Автомобиль")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="uploaded_accident_photos", verbose_name="Загрузил")
    image = models.ImageField("Фотография", upload_to="accident_photos/%Y/%m/%d/")
    description = models.CharField("Описание", max_length=255, blank=True)
    created_at = models.DateTimeField("Дата загрузки", auto_now_add=True)

    class Meta:
        verbose_name = "Фотография ДТП"
        verbose_name_plural = "Фотографии ДТП"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Фото ДТП {self.accident.access_code}"


class WitnessStatement(models.Model):
    accident = models.ForeignKey(Accident, on_delete=models.CASCADE, related_name="witness_statements", verbose_name="ДТП")
    witness_full_name = models.CharField("ФИО свидетеля", max_length=255)
    witness_phone = models.CharField("Телефон свидетеля", max_length=30)
    statement_text = models.TextField("Текст показаний")
    photo = models.ImageField("Фотография", upload_to="witness_photos/%Y/%m/%d/", null=True, blank=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    class Meta:
        verbose_name = "Свидетельское показание"
        verbose_name_plural = "Свидетельские показания"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.witness_full_name} — {self.accident.access_code}"


class SubmissionLog(models.Model):
    accident = models.ForeignKey(Accident, on_delete=models.CASCADE, related_name="submission_logs", verbose_name="ДТП")
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="submission_logs", verbose_name="Отправил")
    submitted_at = models.DateTimeField("Дата и время отправки")
    comment = models.TextField("Служебный комментарий", blank=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    class Meta:
        verbose_name = "Журнал отправки"
        verbose_name_plural = "Журнал отправки"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Отправка {self.accident.access_code} от {self.submitted_at:%d.%m.%Y %H:%M}"
