from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import DriverRegistrationForm, DriverVehicleForm
from .models import DriverProfile


def register(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect("accidents:gibdd_dashboard")
        return redirect("accidents:accident_list")

    if request.method == "POST":
        form = DriverRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Регистрация завершена. Вы вошли в систему.")
            return redirect("accidents:accident_list")
    else:
        form = DriverRegistrationForm()

    return render(request, "users/register.html", {"form": form})


@login_required
def vehicle_add(request):
    if request.user.is_staff:
        return redirect("accidents:gibdd_dashboard")
    profile = DriverProfile.objects.filter(user=request.user).first()
    if not profile:
        messages.error(request, "Для добавления машины нужен профиль водителя.")
        return redirect("accidents:accident_list")

    if request.method == "POST":
        form = DriverVehicleForm(request.POST)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.driver = profile
            vehicle.save()
            messages.success(request, "Машина добавлена в профиль.")
            return redirect("accidents:accident_list")
    else:
        form = DriverVehicleForm(initial={"owner_name": profile.full_name})

    return render(request, "users/vehicle_form.html", {"form": form})
