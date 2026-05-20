from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import DriverProfile


class BootstrapFormMixin:
    def apply_bootstrap(self):
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            else:
                field.widget.attrs.setdefault("class", "form-control")


class DriverRegistrationForm(BootstrapFormMixin, UserCreationForm):
    full_name = forms.CharField(label="ФИО", max_length=255)
    phone = forms.CharField(label="Телефон", max_length=30)
    driver_license_number = forms.CharField(label="Номер водительского удостоверения", max_length=50)

    class Meta:
        model = User
        fields = ("username", "full_name", "phone", "driver_license_number", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()

    def clean_driver_license_number(self):
        value = self.cleaned_data["driver_license_number"].strip()
        if DriverProfile.objects.filter(driver_license_number=value).exists():
            raise forms.ValidationError("Профиль с таким номером водительского удостоверения уже существует.")
        return value

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            DriverProfile.objects.create(
                user=user,
                full_name=self.cleaned_data["full_name"],
                phone=self.cleaned_data["phone"],
                driver_license_number=self.cleaned_data["driver_license_number"],
            )
        return user


class BootstrapAuthenticationForm(BootstrapFormMixin, AuthenticationForm):
    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.apply_bootstrap()
