from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import DriverProfile, DriverVehicle
from .vehicle_validation import clean_insurance_policy_value, clean_license_plate_value, clean_vin_value


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
    vehicle_owner_name = forms.CharField(label="Владелец автомобиля", max_length=255)
    vehicle_brand = forms.CharField(label="Марка автомобиля", max_length=100)
    vehicle_model = forms.CharField(label="Модель автомобиля", max_length=100)
    vehicle_year = forms.IntegerField(label="Год выпуска", min_value=1900, max_value=2100)
    vehicle_license_plate = forms.CharField(label="Государственный номер", max_length=20)
    vehicle_vin = forms.CharField(label="VIN-номер", max_length=17)
    vehicle_insurance_policy = forms.CharField(label="Полис ОСАГО", max_length=20)

    class Meta:
        model = User
        fields = (
            "username",
            "full_name",
            "phone",
            "driver_license_number",
            "vehicle_owner_name",
            "vehicle_brand",
            "vehicle_model",
            "vehicle_year",
            "vehicle_license_plate",
            "vehicle_vin",
            "vehicle_insurance_policy",
            "password1",
            "password2",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vehicle_license_plate"].widget.attrs.update({"placeholder": "А123ВС77"})
        self.fields["vehicle_vin"].widget.attrs.update({"placeholder": "17 символов без I, O, Q"})
        self.fields["vehicle_insurance_policy"].widget.attrs.update({"placeholder": "ЕЕЕ1234567890"})
        self.apply_bootstrap()

    def clean_driver_license_number(self):
        value = self.cleaned_data["driver_license_number"].strip()
        if DriverProfile.objects.filter(driver_license_number=value).exists():
            raise forms.ValidationError("Профиль с таким номером водительского удостоверения уже существует.")
        return value

    def clean_vehicle_license_plate(self):
        return clean_license_plate_value(self.cleaned_data["vehicle_license_plate"])

    def clean_vehicle_vin(self):
        return clean_vin_value(self.cleaned_data["vehicle_vin"])

    def clean_vehicle_insurance_policy(self):
        return clean_insurance_policy_value(self.cleaned_data["vehicle_insurance_policy"])

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            profile = DriverProfile.objects.create(
                user=user,
                full_name=self.cleaned_data["full_name"],
                phone=self.cleaned_data["phone"],
                driver_license_number=self.cleaned_data["driver_license_number"],
            )
            DriverVehicle.objects.create(
                driver=profile,
                owner_name=self.cleaned_data["vehicle_owner_name"],
                brand=self.cleaned_data["vehicle_brand"],
                model=self.cleaned_data["vehicle_model"],
                year=self.cleaned_data["vehicle_year"],
                license_plate=self.cleaned_data["vehicle_license_plate"],
                vin=self.cleaned_data["vehicle_vin"],
                insurance_policy=self.cleaned_data["vehicle_insurance_policy"],
            )
        return user


class BootstrapAuthenticationForm(BootstrapFormMixin, AuthenticationForm):
    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.apply_bootstrap()


class DriverVehicleForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = DriverVehicle
        fields = ("owner_name", "brand", "model", "year", "license_plate", "vin", "insurance_policy")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["license_plate"].widget.attrs.update({"placeholder": "А123ВС77"})
        self.fields["vin"].widget.attrs.update({"placeholder": "17 символов без I, O, Q"})
        self.fields["insurance_policy"].widget.attrs.update({"placeholder": "ЕЕЕ1234567890"})
        self.apply_bootstrap()

    def clean_license_plate(self):
        return clean_license_plate_value(self.cleaned_data["license_plate"])

    def clean_vin(self):
        return clean_vin_value(self.cleaned_data["vin"])

    def clean_insurance_policy(self):
        return clean_insurance_policy_value(self.cleaned_data["insurance_policy"])
