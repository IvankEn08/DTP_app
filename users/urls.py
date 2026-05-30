from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from .forms import BootstrapAuthenticationForm
from . import views


app_name = "users"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("vehicles/add/", views.vehicle_add, name="vehicle_add"),
    path("login/", LoginView.as_view(template_name="users/login.html", authentication_form=BootstrapAuthenticationForm), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
