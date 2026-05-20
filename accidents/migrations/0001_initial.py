import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Accident",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255, verbose_name="Краткое название происшествия")),
                ("accident_date", models.DateTimeField(verbose_name="Дата и время ДТП")),
                ("location", models.CharField(max_length=255, verbose_name="Место происшествия")),
                ("access_code", models.CharField(blank=True, max_length=8, unique=True, verbose_name="Код доступа для свидетелей")),
                ("submitted_at", models.DateTimeField(blank=True, null=True, verbose_name="Дата и время отправки в ГИБДД")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Дата обновления")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="created_accidents", to=settings.AUTH_USER_MODEL, verbose_name="Создатель")),
            ],
            options={
                "verbose_name": "ДТП",
                "verbose_name_plural": "ДТП",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="AccidentDriver",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("responsible", "Виновник"), ("victim", "Пострадавший")], max_length=20, verbose_name="Роль в ДТП")),
                ("comment", models.TextField(blank=True, verbose_name="Комментарий водителя")),
                ("is_ready", models.BooleanField(default=False, verbose_name="Водитель подтвердил заполнение")),
                ("ready_at", models.DateTimeField(blank=True, null=True, verbose_name="Дата подтверждения заполнения")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")),
                ("accident", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="drivers", to="accidents.accident", verbose_name="ДТП")),
                ("driver", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="accident_roles", to="users.driverprofile", verbose_name="Водитель")),
            ],
            options={
                "verbose_name": "Водитель-участник ДТП",
                "verbose_name_plural": "Водители-участники ДТП",
                "ordering": ["created_at"],
            },
        ),
        migrations.CreateModel(
            name="Vehicle",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("brand", models.CharField(max_length=100, verbose_name="Марка")),
                ("model", models.CharField(max_length=100, verbose_name="Модель")),
                ("year", models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1900), django.core.validators.MaxValueValidator(2100)], verbose_name="Год выпуска")),
                ("license_plate", models.CharField(max_length=20, verbose_name="Государственный номер")),
                ("vin", models.CharField(max_length=17, verbose_name="VIN-номер")),
                ("insurance_policy", models.CharField(max_length=20, verbose_name="Номер страхового полиса ОСАГО")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Дата обновления")),
                ("accident", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="vehicles", to="accidents.accident", verbose_name="ДТП")),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="vehicles", to="users.driverprofile", verbose_name="Владелец")),
            ],
            options={
                "verbose_name": "Транспортное средство",
                "verbose_name_plural": "Транспортные средства",
                "ordering": ["brand", "model"],
            },
        ),
        migrations.CreateModel(
            name="AccidentPhoto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="accident_photos/%Y/%m/%d/", verbose_name="Изображение")),
                ("description", models.CharField(blank=True, max_length=255, verbose_name="Описание фотографии")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")),
                ("accident", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="photos", to="accidents.accident", verbose_name="ДТП")),
                ("uploaded_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="uploaded_accident_photos", to=settings.AUTH_USER_MODEL, verbose_name="Загрузил")),
                ("vehicle", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="photos", to="accidents.vehicle", verbose_name="Автомобиль")),
            ],
            options={
                "verbose_name": "Фотография ДТП",
                "verbose_name_plural": "Фотографии ДТП",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Damage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("damage_area", models.CharField(max_length=150, verbose_name="Область повреждения")),
                ("description", models.TextField(verbose_name="Описание повреждения")),
                ("severity", models.CharField(choices=[("minor", "Незначительное"), ("medium", "Среднее"), ("serious", "Серьёзное")], max_length=20, verbose_name="Степень повреждения")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")),
                ("vehicle", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="damages", to="accidents.vehicle", verbose_name="Автомобиль")),
            ],
            options={
                "verbose_name": "Повреждение",
                "verbose_name_plural": "Повреждения",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="SubmissionLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("submitted_at", models.DateTimeField(verbose_name="Дата и время отправки")),
                ("comment", models.TextField(blank=True, verbose_name="Служебный комментарий")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")),
                ("accident", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="submission_logs", to="accidents.accident", verbose_name="ДТП")),
                ("submitted_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="submission_logs", to=settings.AUTH_USER_MODEL, verbose_name="Отправил")),
            ],
            options={
                "verbose_name": "Журнал отправки",
                "verbose_name_plural": "Журнал отправки",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="WitnessStatement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("witness_full_name", models.CharField(max_length=255, verbose_name="ФИО свидетеля")),
                ("witness_phone", models.CharField(max_length=30, verbose_name="Телефон свидетеля")),
                ("statement_text", models.TextField(verbose_name="Текст показаний")),
                ("photo", models.ImageField(blank=True, null=True, upload_to="witness_photos/%Y/%m/%d/", verbose_name="Фотография")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")),
                ("accident", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="witness_statements", to="accidents.accident", verbose_name="ДТП")),
            ],
            options={
                "verbose_name": "Свидетельское показание",
                "verbose_name_plural": "Свидетельские показания",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="accidentdriver",
            constraint=models.UniqueConstraint(fields=("accident", "driver"), name="unique_accident_driver"),
        ),
    ]
