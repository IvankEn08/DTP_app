import io
import json
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from users.models import DriverProfile
from .forms import (
    AccidentCreateForm,
    AccidentDriverForm,
    AccidentPhotoForm,
    AccidentUpdateForm,
    DamageForm,
    DriverJoinCodeForm,
    DriverCommentForm,
    SubmissionConfirmForm,
    VehicleForm,
    WitnessCodeForm,
    WitnessStatementForm,
)
from .models import Accident, AccidentDriver, Damage, SubmissionLog, Vehicle, WitnessStatement


def home(request):
    return render(request, "accidents/home.html")


def is_gibdd_staff(user):
    return user.is_authenticated and user.is_staff


def get_driver_profile(user):
    if not user.is_authenticated:
        return None
    return DriverProfile.objects.filter(user=user).first()


def get_user_participant(user, accident):
    if not user.is_authenticated:
        return None
    return accident.drivers.select_related("driver", "driver__user").filter(driver__user=user).first()


def user_is_participant(user, accident):
    return get_user_participant(user, accident) is not None


def user_can_view_accident(user, accident):
    if not user.is_authenticated:
        return False
    return is_gibdd_staff(user) or accident.created_by_id == user.id or user_is_participant(user, accident)


def user_can_edit_accident(user, accident):
    return user_can_view_accident(user, accident) and not accident.is_submitted and accident.created_by_id == user.id


def user_can_modify_data(user, accident):
    return user_can_view_accident(user, accident) and not accident.is_submitted and (accident.created_by_id == user.id or user_is_participant(user, accident))


def user_can_manage_drivers(user, accident):
    return user_can_view_accident(user, accident) and not accident.is_submitted and accident.created_by_id == user.id


def opposite_role(role):
    if role == AccidentDriver.Role.RESPONSIBLE:
        return AccidentDriver.Role.VICTIM
    return AccidentDriver.Role.RESPONSIBLE


def accident_has_two_drivers(accident):
    return accident.drivers.count() == 2


def accident_drivers_are_ready(accident):
    return accident_has_two_drivers(accident) and not accident.drivers.filter(is_ready=False).exists()


def reset_participant_ready(participant):
    if participant and participant.is_ready:
        participant.is_ready = False
        participant.ready_at = None
        participant.save(update_fields=["is_ready", "ready_at"])


def reset_driver_ready(accident, driver_profile):
    participant = accident.drivers.filter(driver=driver_profile).first()
    reset_participant_ready(participant)


def reset_all_drivers_ready(accident):
    accident.drivers.update(is_ready=False, ready_at=None)


def user_can_submit(user, accident):
    if not user_can_view_accident(user, accident) or accident.is_submitted:
        return False
    if not accident_drivers_are_ready(accident):
        return False
    if is_gibdd_staff(user):
        return True
    participant = get_user_participant(user, accident)
    return participant is not None and participant.role == AccidentDriver.Role.RESPONSIBLE


def submit_blocker_message(user, accident):
    if accident.is_submitted:
        return "ДТП уже отправлено в ГИБДД."
    if accident.drivers.count() < 2:
        return "Для отправки нужно добавить двух водителей-участников."
    if not accident_drivers_are_ready(accident):
        return "Отправка станет доступна после подтверждения заполнения обоими водителями."
    if is_gibdd_staff(user):
        return ""
    participant = get_user_participant(user, accident)
    if participant is None:
        return "Отправить заявление может только участник ДТП."
    if participant.role != AccidentDriver.Role.RESPONSIBLE:
        return "Отправить заявление может только водитель с ролью «Виновник»."
    return ""


def get_accessible_accident(user, pk):
    accident = get_object_or_404(
        Accident.objects.select_related("created_by"),
        pk=pk,
    )
    if not user_can_view_accident(user, accident):
        return None
    return accident


def get_driver_visible_accidents(user, profile):
    created_accidents = Accident.objects.filter(created_by=user)
    participant_accidents = Accident.objects.none()
    if profile:
        participant_accidents = (
            Accident.objects.filter(drivers__driver=profile)
            .exclude(created_by=user)
            .distinct()
        )
    return created_accidents, participant_accidents


def certificate_font(size, bold=False):
    font_name = "arialbd.ttf" if bold else "arial.ttf"
    font_path = Path("C:/Windows/Fonts") / font_name
    if font_path.exists():
        return ImageFont.truetype(str(font_path), size)
    return ImageFont.load_default()


def draw_centered_text(draw, box, text_value, font, fill):
    left, top, right, bottom = box
    words = text_value.split()
    lines = []
    current = ""
    max_width = right - left
    for word in words:
        candidate = word if not current else f"{current} {word}"
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    line_height = font.size + 8 if hasattr(font, "size") else 28
    total_height = len(lines) * line_height
    y = top + ((bottom - top) - total_height) / 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        x = left + (max_width - (bbox[2] - bbox[0])) / 2
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height


def build_driver_certificate(profile, accidents):
    width, height = 1754, 1240
    image = Image.new("RGB", (width, height), "#e9f8ff")
    draw = ImageDraw.Draw(image)

    title_font = certificate_font(54, True)
    subtitle_font = certificate_font(34, False)
    name_font = certificate_font(46, True)
    text_font = certificate_font(30, False)
    small_font = certificate_font(23, False)
    count = accidents.count()

    draw.rectangle((0, 760, width, height), fill="#b7ec8f")
    draw.polygon([(0, 930), (width, 820), (width, height), (0, height)], fill="#77d861")
    draw.polygon([(700, height), (1055, height), (960, 760), (805, 760)], fill="#4b4b4b")
    for y in range(805, height, 92):
        draw.rectangle((866, y, 892, y + 48), fill="#fff6a8")

    draw.ellipse((1325, 95, 1545, 315), fill="#ffd23f", outline="#f4a900", width=7)
    for angle_x, angle_y in ((1285, 145), (1552, 155), (1350, 45), (1490, 40), (1310, 305), (1535, 302)):
        draw.line((1435, 205, angle_x, angle_y), fill="#ffd23f", width=10)
    draw.ellipse((1380, 170, 1415, 205), fill="#442800")
    draw.ellipse((1470, 170, 1505, 205), fill="#442800")
    draw.arc((1405, 190, 1490, 255), 10, 170, fill="#442800", width=6)

    for cloud in ((155, 125, 360, 215), (440, 95, 680, 190), (1125, 120, 1305, 205)):
        x1, y1, x2, y2 = cloud
        draw.ellipse((x1, y1 + 35, x1 + 100, y2), fill="white")
        draw.ellipse((x1 + 60, y1, x1 + 180, y2), fill="white")
        draw.ellipse((x1 + 145, y1 + 30, x2, y2), fill="white")
        draw.rectangle((x1 + 45, y1 + 75, x2 - 35, y2), fill="white")

    colors = ["#ff5b6e", "#36c2ff", "#ffe156", "#7bd88f", "#c084fc"]
    for index, color in enumerate(colors):
        x = 175 + index * 70
        y = 285 + (index % 2) * 35
        draw.ellipse((x, y, x + 55, y + 75), fill=color, outline="#ffffff", width=3)
        draw.line((x + 28, y + 75, x + 10, y + 150), fill="#888888", width=2)

    draw.rounded_rectangle((110, 95, width - 110, height - 95), radius=46, outline="#f7b733", width=12)
    draw.rounded_rectangle((145, 130, width - 145, height - 130), radius=34, outline="#ffffff", width=8)
    draw.rounded_rectangle((190, 355, width - 190, 1080), radius=36, fill="#fffdf4", outline="#f2c94c", width=5)
    draw.rectangle((250, 355, width - 250, 430), fill="#ff6f61")
    draw.polygon([(190, 355), (250, 355), (250, 430), (190, 455)], fill="#d94f45")
    draw.polygon([(width - 190, 355), (width - 250, 355), (width - 250, 430), (width - 190, 455)], fill="#d94f45")

    draw_centered_text(draw, (240, 370, width - 240, 430), "ПОЧЁТНАЯ ГРАМОТА", title_font, "#ffffff")
    draw_centered_text(draw, (180, 170, width - 180, 310), "Справка по истории ДТП", subtitle_font, "#1f3b57")
    draw_centered_text(draw, (240, 475, width - 240, 565), profile.full_name, name_font, "#111111")
    draw_centered_text(draw, (290, 595, width - 290, 705), f"За всё время у вас целых {count} аварий. Так держать!", text_font, "#333333")

    y = 760
    draw.text((300, y), "Последние карточки ДТП:", font=text_font, fill="#1f3b57")
    y += 55
    for accident in accidents.order_by("-accident_date")[:5]:
        line = f"{accident.accident_date:%d.%m.%Y} — {accident.title} — {accident.location}"
        draw.text((280, y), line[:95], font=small_font, fill="#333333")
        y += 36
    if count == 0:
        draw.text((280, y), "Пока ни одной аварии. История ДТП пуста.", font=small_font, fill="#333333")

    buffer = io.BytesIO()
    image.save(buffer, format="PDF", resolution=150.0)
    buffer.seek(0)
    return buffer


@login_required
def accident_list(request):
    if is_gibdd_staff(request.user):
        return redirect("accidents:gibdd_dashboard")

    profile = get_driver_profile(request.user)
    created_accidents, participant_accidents = get_driver_visible_accidents(request.user, profile)

    return render(
        request,
        "accidents/accident_list.html",
        {
            "profile": profile,
            "created_accidents": created_accidents,
            "participant_accidents": participant_accidents,
            "join_form": DriverJoinCodeForm(),
            "registered_vehicles": profile.registered_vehicles.all() if profile else [],
        },
    )


@login_required
def driver_join(request):
    if is_gibdd_staff(request.user):
        return redirect("accidents:gibdd_dashboard")
    profile = get_driver_profile(request.user)
    if not profile:
        messages.error(request, "Для присоединения к ДТП нужен профиль водителя.")
        return redirect("accidents:accident_list")
    if request.method != "POST":
        return redirect("accidents:accident_list")

    form = DriverJoinCodeForm(request.POST)
    if form.is_valid():
        code = form.cleaned_data["driver_join_code"]
        accident = Accident.objects.filter(driver_join_code=code).first()
        if not accident:
            messages.error(request, "ДТП с таким кодом второго водителя не найдено.")
            return redirect("accidents:accident_list")
        if accident.is_submitted:
            messages.error(request, "Это ДТП уже отправлено в ГИБДД.")
            return redirect("accidents:accident_list")
        if accident.drivers.filter(driver=profile).exists():
            messages.info(request, "Вы уже являетесь участником этого ДТП.")
            return redirect("accidents:detail", pk=accident.pk)
        if accident.drivers.count() >= 2:
            messages.error(request, "В этом ДТП уже указаны два водителя.")
            return redirect("accidents:accident_list")
        with transaction.atomic():
            accident = Accident.objects.select_for_update().get(pk=accident.pk)
            first_participant = accident.drivers.select_for_update().first()
            if first_participant:
                first_participant.role = opposite_role(accident.second_driver_role)
                first_participant.is_ready = False
                first_participant.ready_at = None
                first_participant.save(update_fields=["role", "is_ready", "ready_at"])
            AccidentDriver.objects.create(
                accident=accident,
                driver=profile,
                role=accident.second_driver_role,
            )
        messages.success(request, "Вы присоединились к ДТП. Проверьте данные и заполните свой комментарий.")
        return redirect("accidents:detail", pk=accident.pk)

    for error in form.errors.values():
        messages.error(request, error)
    return redirect("accidents:accident_list")


@login_required
def driver_accidents_certificate(request):
    if is_gibdd_staff(request.user):
        return redirect("accidents:gibdd_dashboard")
    profile = get_driver_profile(request.user)
    if not profile:
        messages.error(request, "Для экспорта нужен профиль водителя.")
        return redirect("accidents:accident_list")
    accidents = Accident.objects.filter(Q(created_by=request.user) | Q(drivers__driver=profile)).distinct()
    buffer = build_driver_certificate(profile, accidents)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="dtp_certificate.pdf"'
    return response


@login_required
def gibdd_dashboard(request):
    if not is_gibdd_staff(request.user):
        return HttpResponseForbidden("Доступ разрешен только сотруднику ГИБДД.")

    accidents = Accident.objects.all()
    total_accidents = accidents.count()
    submitted_accidents = accidents.filter(submitted_at__isnull=False).count()
    not_submitted_accidents = total_accidents - submitted_accidents
    total_drivers = DriverProfile.objects.count()
    total_vehicles = Vehicle.objects.count()
    total_witnesses = WitnessStatement.objects.count()

    monthly_rows = (
        accidents.annotate(month=TruncMonth("accident_date"))
        .values("month")
        .annotate(total=Count("id"))
        .order_by("month")
    )
    monthly_labels = [row["month"].strftime("%m.%Y") for row in monthly_rows if row["month"]]
    monthly_values = [row["total"] for row in monthly_rows if row["month"]]

    severity_rows = (
        Damage.objects.values("severity")
        .annotate(total=Count("id"))
        .order_by("severity")
    )
    severity_labels = [dict(Damage.Severity.choices).get(row["severity"], row["severity"]) for row in severity_rows]
    severity_values = [row["total"] for row in severity_rows]

    brand_rows = (
        Vehicle.objects.values("brand")
        .annotate(total=Count("id"))
        .order_by("-total", "brand")[:8]
    )
    brand_labels = [row["brand"] for row in brand_rows]
    brand_values = [row["total"] for row in brand_rows]

    context = {
        "total_accidents": total_accidents,
        "submitted_accidents": submitted_accidents,
        "not_submitted_accidents": not_submitted_accidents,
        "total_drivers": total_drivers,
        "total_vehicles": total_vehicles,
        "total_witnesses": total_witnesses,
        "monthly_labels": json.dumps(monthly_labels, ensure_ascii=False),
        "monthly_values": json.dumps(monthly_values),
        "status_values": json.dumps([submitted_accidents, not_submitted_accidents]),
        "severity_labels": json.dumps(severity_labels, ensure_ascii=False),
        "severity_values": json.dumps(severity_values),
        "brand_labels": json.dumps(brand_labels, ensure_ascii=False),
        "brand_values": json.dumps(brand_values),
    }
    return render(request, "accidents/gibdd_dashboard.html", context)


@login_required
def gibdd_accident_list(request):
    if not is_gibdd_staff(request.user):
        return HttpResponseForbidden("Доступ разрешен только сотруднику ГИБДД.")

    sort_options = {
        "date_desc": ("-accident_date", "Дата ДТП: новые сначала"),
        "date_asc": ("accident_date", "Дата ДТП: старые сначала"),
        "created_desc": ("-created_at", "Дата создания: новые сначала"),
        "submitted_desc": ("-submitted_at", "-created_at", "Отправленные сначала"),
        "title": ("title", "Название"),
        "location": ("location", "Место"),
    }
    selected_sort = request.GET.get("sort", "date_desc")
    sort_definition = sort_options.get(selected_sort, sort_options["date_desc"])
    order_by = sort_definition[:-1]

    accidents = (
        Accident.objects.select_related("created_by")
        .prefetch_related("drivers__driver", "vehicles", "photos")
        .order_by(*order_by)
    )

    return render(
        request,
        "accidents/gibdd_accident_list.html",
        {
            "accidents": accidents,
            "sort_options": [(key, value[-1]) for key, value in sort_options.items()],
            "selected_sort": selected_sort,
        },
    )


@login_required
def accident_create(request):
    profile = get_driver_profile(request.user)
    if not profile:
        messages.error(request, "Для создания ДТП нужен профиль водителя.")
        return redirect("accidents:accident_list")

    if request.method == "POST":
        form = AccidentCreateForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                accident = form.save(commit=False)
                accident.created_by = request.user
                accident.save()
                AccidentDriver.objects.create(
                    accident=accident,
                    driver=profile,
                    role=AccidentDriver.Role.VICTIM,
                    comment=form.cleaned_data["driver_comment"],
                )
            messages.success(request, "Карточка ДТП создана. Добавьте автомобиль, второго водителя и дождитесь подтверждения обоих участников.")
            return redirect("accidents:detail", pk=accident.pk)
    else:
        form = AccidentCreateForm()

    return render(request, "accidents/accident_form.html", {"form": form, "title": "Создание ДТП", "button_text": "Создать ДТП"})


@login_required
def accident_detail(request, pk):
    accident = get_accessible_accident(request.user, pk)
    if accident is None:
        return HttpResponseForbidden("У вас нет доступа к этому ДТП.")
    if not accident.driver_join_code and not accident.is_submitted:
        accident.save(update_fields=["driver_join_code", "updated_at"])

    drivers = accident.drivers.select_related("driver", "driver__user")
    vehicles = accident.vehicles.select_related("owner").prefetch_related("damages")
    photos = accident.photos.select_related("vehicle", "uploaded_by")
    witness_statements = accident.witness_statements.all()
    submission_logs = accident.submission_logs.select_related("submitted_by")
    current_participant = get_user_participant(request.user, accident)
    blocker = "" if is_gibdd_staff(request.user) else submit_blocker_message(request.user, accident)

    return render(
        request,
        "accidents/accident_detail.html",
        {
            "accident": accident,
            "drivers": drivers,
            "vehicles": vehicles,
            "photos": photos,
            "witness_statements": witness_statements,
            "submission_logs": submission_logs,
            "current_participant": current_participant,
            "can_edit": user_can_edit_accident(request.user, accident),
            "can_modify_data": user_can_modify_data(request.user, accident),
            "can_manage_drivers": user_can_manage_drivers(request.user, accident) and accident.drivers.count() < 2,
            "can_edit_comment": current_participant is not None and not accident.is_submitted,
            "can_toggle_ready": current_participant is not None and not accident.is_submitted,
            "can_submit": user_can_submit(request.user, accident),
            "submit_blocker": blocker,
            "drivers_ready": accident_drivers_are_ready(accident),
        },
    )


@login_required
def accident_edit(request, pk):
    accident = get_accessible_accident(request.user, pk)
    if accident is None:
        return HttpResponseForbidden("У вас нет доступа к этому ДТП.")
    if not user_can_edit_accident(request.user, accident):
        messages.error(request, "Редактирование этого ДТП недоступно.")
        return redirect("accidents:detail", pk=accident.pk)

    if request.method == "POST":
        form = AccidentUpdateForm(request.POST, instance=accident)
        if form.is_valid():
            form.save()
            if form.changed_data:
                reset_all_drivers_ready(accident)
                messages.success(request, "Данные ДТП обновлены. Подтверждения водителей сброшены.")
            else:
                messages.success(request, "Данные ДТП обновлены.")
            return redirect("accidents:detail", pk=accident.pk)
    else:
        form = AccidentUpdateForm(instance=accident)

    return render(request, "accidents/accident_form.html", {"form": form, "title": "Редактирование ДТП", "button_text": "Сохранить"})


@login_required
def accident_delete(request, pk):
    accident = get_accessible_accident(request.user, pk)
    if accident is None:
        return HttpResponseForbidden("У вас нет доступа к этому ДТП.")
    if not user_can_edit_accident(request.user, accident):
        messages.error(request, "Удаление этого ДТП недоступно.")
        return redirect("accidents:detail", pk=accident.pk)

    if request.method == "POST":
        accident.delete()
        messages.success(request, "Карточка ДТП удалена.")
        return redirect("accidents:accident_list")

    return render(request, "accidents/accident_confirm_delete.html", {"accident": accident})


@login_required
def accident_driver_add(request, pk):
    accident = get_accessible_accident(request.user, pk)
    if accident is None:
        return HttpResponseForbidden("У вас нет доступа к этому ДТП.")
    if not user_can_manage_drivers(request.user, accident):
        messages.error(request, "Добавление участников недоступно.")
        return redirect("accidents:detail", pk=accident.pk)
    if accident.drivers.count() >= 2:
        messages.error(request, "В ДТП можно добавить только двух водителей.")
        return redirect("accidents:detail", pk=accident.pk)

    if request.method == "POST":
        form = AccidentDriverForm(request.POST, accident=accident)
        if form.is_valid():
            with transaction.atomic():
                existing_participant = get_user_participant(request.user, accident)
                if existing_participant is None:
                    existing_participant = accident.drivers.select_for_update().first()
                second_role = form.cleaned_data["role"]
                existing_participant.role = opposite_role(second_role)
                existing_participant.is_ready = False
                existing_participant.ready_at = None
                existing_participant.save(update_fields=["role", "is_ready", "ready_at"])
                accident.second_driver_role = second_role
                if not accident.driver_join_code:
                    accident.save(update_fields=["second_driver_role", "driver_join_code", "updated_at"])
                else:
                    accident.save(update_fields=["second_driver_role", "updated_at"])
            messages.success(request, "Код второго водителя подготовлен. Передайте его зарегистрированному водителю.")
            return redirect("accidents:detail", pk=accident.pk)
    else:
        form = AccidentDriverForm(accident=accident, initial={"role": accident.second_driver_role})

    return render(request, "accidents/driver_form.html", {"form": form, "accident": accident})


@login_required
def driver_comment_edit(request, pk):
    accident = get_accessible_accident(request.user, pk)
    if accident is None:
        return HttpResponseForbidden("У вас нет доступа к этому ДТП.")
    participant = get_user_participant(request.user, accident)
    if participant is None:
        return HttpResponseForbidden("Редактировать комментарий может только участник ДТП.")
    if accident.is_submitted:
        messages.error(request, "После отправки ДТП комментарии редактировать нельзя.")
        return redirect("accidents:detail", pk=accident.pk)

    old_comment = participant.comment
    if request.method == "POST":
        form = DriverCommentForm(request.POST, instance=participant)
        if form.is_valid():
            updated = form.save(commit=False)
            if old_comment != updated.comment:
                updated.is_ready = False
                updated.ready_at = None
            updated.save()
            messages.success(request, "Комментарий сохранен. Если он был изменен, подтвердите готовность заново.")
            return redirect("accidents:detail", pk=accident.pk)
    else:
        form = DriverCommentForm(instance=participant)

    return render(request, "accidents/driver_comment_form.html", {"form": form, "accident": accident})


@login_required
def driver_ready_toggle(request, pk):
    accident = get_accessible_accident(request.user, pk)
    if accident is None:
        return HttpResponseForbidden("У вас нет доступа к этому ДТП.")
    participant = get_user_participant(request.user, accident)
    if participant is None:
        return HttpResponseForbidden("Подтверждать готовность может только участник ДТП.")
    if accident.is_submitted:
        messages.error(request, "После отправки ДТП готовность изменить нельзя.")
        return redirect("accidents:detail", pk=accident.pk)
    if request.method != "POST":
        return redirect("accidents:detail", pk=accident.pk)

    participant.is_ready = not participant.is_ready
    participant.ready_at = timezone.now() if participant.is_ready else None
    participant.save(update_fields=["is_ready", "ready_at"])
    if participant.is_ready:
        messages.success(request, "Вы подтвердили, что все данные заполнены.")
    else:
        messages.info(request, "Подтверждение готовности снято.")
    return redirect("accidents:detail", pk=accident.pk)


@login_required
def vehicle_add(request, pk):
    accident = get_accessible_accident(request.user, pk)
    if accident is None:
        return HttpResponseForbidden("У вас нет доступа к этому ДТП.")
    if not user_can_modify_data(request.user, accident):
        messages.error(request, "Добавление автомобиля недоступно.")
        return redirect("accidents:detail", pk=accident.pk)

    profile = get_driver_profile(request.user)
    if not profile:
        messages.error(request, "Для добавления автомобиля нужен профиль водителя.")
        return redirect("accidents:detail", pk=accident.pk)
    if not profile.registered_vehicles.exists():
        messages.error(request, "Сначала добавьте автомобиль в свой профиль.")
        return redirect("users:vehicle_add")

    if request.method == "POST":
        form = VehicleForm(request.POST, owner_profile=profile)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.accident = accident
            vehicle.save()
            reset_driver_ready(accident, vehicle.owner)
            messages.success(request, "Автомобиль добавлен.")
            return redirect("accidents:detail", pk=accident.pk)
    else:
        form = VehicleForm(owner_profile=profile)

    return render(request, "accidents/vehicle_form.html", {"form": form, "accident": accident})


@login_required
def damage_add(request, pk):
    accident = get_accessible_accident(request.user, pk)
    if accident is None:
        return HttpResponseForbidden("У вас нет доступа к этому ДТП.")
    if not user_can_modify_data(request.user, accident):
        messages.error(request, "Добавление повреждения недоступно.")
        return redirect("accidents:detail", pk=accident.pk)

    profile = get_driver_profile(request.user)
    vehicles = Vehicle.objects.filter(accident=accident, owner=profile).select_related("owner") if profile else Vehicle.objects.none()

    if not vehicles.exists():
        messages.error(request, "Сначала добавьте автомобиль.")
        return redirect("accidents:detail", pk=accident.pk)

    if request.method == "POST":
        form = DamageForm(request.POST, vehicles_queryset=vehicles)
        if form.is_valid():
            damage = form.save()
            reset_driver_ready(accident, damage.vehicle.owner)
            messages.success(request, "Повреждение добавлено.")
            return redirect("accidents:detail", pk=accident.pk)
    else:
        form = DamageForm(vehicles_queryset=vehicles)

    return render(request, "accidents/damage_form.html", {"form": form, "accident": accident})


@login_required
def photo_add(request, pk):
    accident = get_accessible_accident(request.user, pk)
    if accident is None:
        return HttpResponseForbidden("У вас нет доступа к этому ДТП.")
    if not user_can_modify_data(request.user, accident):
        messages.error(request, "Добавление фотографий недоступно.")
        return redirect("accidents:detail", pk=accident.pk)

    profile = get_driver_profile(request.user)
    if profile:
        vehicles = Vehicle.objects.filter(accident=accident, owner=profile).select_related("owner")
    else:
        vehicles = Vehicle.objects.filter(accident=accident).select_related("owner")

    if request.method == "POST":
        form = AccidentPhotoForm(request.POST, request.FILES, vehicles_queryset=vehicles)
        if form.is_valid():
            photo = form.save(commit=False)
            photo.accident = accident
            photo.uploaded_by = request.user
            photo.save()
            if photo.vehicle:
                reset_driver_ready(accident, photo.vehicle.owner)
            else:
                reset_participant_ready(get_user_participant(request.user, accident))
            messages.success(request, "Фотография добавлена.")
            return redirect("accidents:detail", pk=accident.pk)
    else:
        form = AccidentPhotoForm(vehicles_queryset=vehicles)

    return render(request, "accidents/photo_form.html", {"form": form, "accident": accident})


@login_required
def submit_confirm(request, pk):
    accident = get_accessible_accident(request.user, pk)
    if accident is None:
        return HttpResponseForbidden("У вас нет доступа к этому ДТП.")
    if accident.is_submitted:
        return redirect("accidents:submit_success", pk=accident.pk)

    blocker = submit_blocker_message(request.user, accident)
    if blocker:
        messages.error(request, blocker)
        return redirect("accidents:detail", pk=accident.pk)

    if request.method == "POST":
        form = SubmissionConfirmForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                accident = Accident.objects.select_for_update().get(pk=accident.pk)
                accident.submitted_at = timezone.now()
                accident.save(update_fields=["submitted_at", "updated_at"])
                SubmissionLog.objects.create(
                    accident=accident,
                    submitted_by=request.user,
                    submitted_at=accident.submitted_at,
                    comment="Отправлено в ГИБДД.",
                )
            messages.success(request, "ДТП отправлено в ГИБДД.")
            return redirect("accidents:submit_success", pk=accident.pk)
    else:
        form = SubmissionConfirmForm()

    return render(
        request,
        "accidents/submission_confirm.html",
        {
            "accident": accident,
            "drivers": accident.drivers.select_related("driver"),
            "vehicles": accident.vehicles.select_related("owner").prefetch_related("damages"),
            "photos": accident.photos.select_related("vehicle", "uploaded_by"),
            "witness_statements": accident.witness_statements.all(),
            "form": form,
        },
    )


@login_required
def submit_success(request, pk):
    accident = get_accessible_accident(request.user, pk)
    if accident is None:
        return HttpResponseForbidden("У вас нет доступа к этому ДТП.")
    return render(request, "accidents/submission_success.html", {"accident": accident})


def witness_code(request):
    if request.method == "POST":
        form = WitnessCodeForm(request.POST)
        if form.is_valid():
            access_code = form.cleaned_data["access_code"]
            accident = Accident.objects.filter(access_code=access_code).first()
            if accident:
                if accident.is_submitted:
                    messages.error(request, "Сбор свидетельских показаний по этому ДТП уже завершен.")
                    return redirect("accidents:witness_code")
                return redirect("accidents:witness_statement", access_code=access_code)
            messages.error(request, "ДТП с таким кодом не найдено.")
    else:
        form = WitnessCodeForm()

    return render(request, "accidents/witness_code_form.html", {"form": form})


def witness_statement(request, access_code):
    accident = get_object_or_404(Accident, access_code=access_code.upper())
    if accident.is_submitted:
        messages.error(request, "Сбор свидетельских показаний по этому ДТП уже завершен.")
        return redirect("accidents:witness_code")

    if request.method == "POST":
        form = WitnessStatementForm(request.POST, request.FILES)
        if form.is_valid():
            statement = form.save(commit=False)
            statement.accident = accident
            statement.save()
            messages.success(request, "Ваши показания сохранены.")
            return redirect("accidents:witness_success")
    else:
        form = WitnessStatementForm()

    return render(request, "accidents/witness_statement_form.html", {"form": form, "accident": accident})


def witness_success(request):
    return render(request, "accidents/witness_success.html")
