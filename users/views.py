from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render

from .forms import DriverRegistrationForm


def register(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect("accidents:gibdd_list")
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
