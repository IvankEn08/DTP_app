from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from users.models import DriverProfile
from .forms import (
    AccidentCreateForm,
    AccidentDriverForm,
    AccidentPhotoForm,
    AccidentUpdateForm,
    DamageForm,
    DriverCommentForm,
    SubmissionConfirmForm,
    VehicleForm,
    WitnessCodeForm,
    WitnessStatementForm,
)
from .models import Accident, AccidentDriver, SubmissionLog, Vehicle


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
    participant = get_user_participant(user, accident)
    return participant is not None and participant.role == AccidentDriver.Role.VICTIM


def submit_blocker_message(user, accident):
    if accident.is_submitted:
        return "ДТП уже отправлено в ГИБДД."
    if accident.drivers.count() < 2:
        return "Для отправки нужно добавить двух водителей-участников."
    if not accident_drivers_are_ready(accident):
        return "Отправка станет доступна после подтверждения заполнения обоими водителями."
    participant = get_user_participant(user, accident)
    if participant is None:
        return "Отправить заявление может только участник ДТП."
    if participant.role != AccidentDriver.Role.VICTIM:
        return "Отправить заявление может только водитель с ролью «Пострадавший»."
    return ""


def get_accessible_accident(user, pk):
    accident = get_object_or_404(
        Accident.objects.select_related("created_by"),
        pk=pk,
    )
    if not user_can_view_accident(user, accident):
        return None
    return accident


@login_required
def accident_list(request):
    if is_gibdd_staff(request.user):
        return redirect("accidents:gibdd_list")

    profile = get_driver_profile(request.user)
    created_accidents = Accident.objects.filter(created_by=request.user)
    participant_accidents = Accident.objects.none()

    if profile:
        participant_accidents = (
            Accident.objects.filter(drivers__driver=profile)
            .exclude(created_by=request.user)
            .distinct()
        )

    return render(
        request,
        "accidents/accident_list.html",
        {
            "profile": profile,
            "created_accidents": created_accidents,
            "participant_accidents": participant_accidents,
        },
    )


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
            accident = form.save(commit=False)
            accident.created_by = request.user
            accident.save()
            AccidentDriver.objects.create(
                accident=accident,
                driver=profile,
                role=AccidentDriver.Role.VICTIM,
                comment=form.cleaned_data["driver_comment"],
            )
            messages.success(request, "Карточка ДТП создана. Добавьте второго водителя и дождитесь подтверждения обоих участников.")
            return redirect("accidents:detail", pk=accident.pk)
    else:
        form = AccidentCreateForm()

    return render(request, "accidents/accident_form.html", {"form": form, "title": "Создание ДТП", "button_text": "Создать ДТП"})


@login_required
def accident_detail(request, pk):
    accident = get_accessible_accident(request.user, pk)
    if accident is None:
        return HttpResponseForbidden("У вас нет доступа к этому ДТП.")

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
                AccidentDriver.objects.create(
                    accident=accident,
                    driver=form.cleaned_data["driver"],
                    role=second_role,
                )
            messages.success(request, "Второй водитель добавлен. Оба водителя должны подтвердить готовность перед отправкой.")
            return redirect("accidents:detail", pk=accident.pk)
    else:
        form = AccidentDriverForm(accident=accident)

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

    owners = DriverProfile.objects.filter(accident_roles__accident=accident).distinct()
    profile = get_driver_profile(request.user)
    if accident.created_by_id != request.user.id:
        owners = owners.filter(pk=profile.pk) if profile else owners.none()

    if request.method == "POST":
        form = VehicleForm(request.POST, owners_queryset=owners)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.accident = accident
            vehicle.save()
            reset_driver_ready(accident, vehicle.owner)
            messages.success(request, "Автомобиль добавлен.")
            return redirect("accidents:detail", pk=accident.pk)
    else:
        form = VehicleForm(owners_queryset=owners)

    return render(request, "accidents/vehicle_form.html", {"form": form, "accident": accident})


@login_required
def damage_add(request, pk):
    accident = get_accessible_accident(request.user, pk)
    if accident is None:
        return HttpResponseForbidden("У вас нет доступа к этому ДТП.")
    if not user_can_modify_data(request.user, accident):
        messages.error(request, "Добавление повреждения недоступно.")
        return redirect("accidents:detail", pk=accident.pk)

    vehicles = Vehicle.objects.filter(accident=accident).select_related("owner")
    profile = get_driver_profile(request.user)
    if accident.created_by_id != request.user.id:
        vehicles = vehicles.filter(owner=profile) if profile else vehicles.none()

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
        messages.error(request, "Загрузка фотографий недоступна.")
        return redirect("accidents:detail", pk=accident.pk)

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
            messages.success(request, "Фотография загружена.")
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
