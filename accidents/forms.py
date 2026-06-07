from django import forms

from users.models import DriverVehicle
from .models import Accident, AccidentDriver, AccidentPhoto, Damage, Vehicle, WitnessStatement


class BootstrapFormMixin:
    def apply_bootstrap(self):
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(field.widget, forms.FileInput):
                field.widget.attrs.setdefault("class", "form-control")
            elif isinstance(field.widget, forms.RadioSelect):
                continue
            else:
                field.widget.attrs.setdefault("class", "form-control")


class AccidentCreateForm(BootstrapFormMixin, forms.ModelForm):
    accident_date = forms.DateTimeField(
        label="Дата и время ДТП",
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
    )
    driver_comment = forms.CharField(
        label="Ваш комментарий по обстоятельствам ДТП",
        widget=forms.Textarea(attrs={"rows": 5}),
        required=True,
    )

    class Meta:
        model = Accident
        fields = ("title", "accident_date", "location")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()


class AccidentUpdateForm(BootstrapFormMixin, forms.ModelForm):
    accident_date = forms.DateTimeField(
        label="Дата и время ДТП",
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
    )

    class Meta:
        model = Accident
        fields = ("title", "accident_date", "location")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()


class AccidentDriverForm(BootstrapFormMixin, forms.Form):
    role = forms.ChoiceField(label="Роль второго водителя", choices=AccidentDriver.Role.choices)

    def __init__(self, *args, accident=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.accident = accident
        self.apply_bootstrap()


class DriverJoinCodeForm(BootstrapFormMixin, forms.Form):
    driver_join_code = forms.CharField(label="Код второго водителя", max_length=8)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["driver_join_code"].widget.attrs.update({"placeholder": "Например, D1R2V3R4"})
        self.apply_bootstrap()

    def clean_driver_join_code(self):
        return self.cleaned_data["driver_join_code"].strip().upper()


class DriverCommentForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = AccidentDriver
        fields = ("comment",)
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()


class VehicleForm(BootstrapFormMixin, forms.ModelForm):
    registered_vehicle = forms.ModelChoiceField(
        label="Автомобиль",
        queryset=DriverVehicle.objects.none(),
        empty_label="Выберите автомобиль",
    )

    class Meta:
        model = Vehicle
        fields = ()

    def __init__(self, *args, owner_profile=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner_profile = owner_profile
        self.selected_registered_vehicle = None
        if owner_profile is not None:
            self.fields["registered_vehicle"].queryset = owner_profile.registered_vehicles.all()
        self.apply_bootstrap()

    def clean(self):
        cleaned_data = super().clean()
        registered_vehicle = cleaned_data.get("registered_vehicle")
        if registered_vehicle is None:
            self.add_error("registered_vehicle", "Выберите автомобиль из своего профиля.")
        elif self.owner_profile and registered_vehicle.driver_id != self.owner_profile.id:
            self.add_error("registered_vehicle", "Для ДТП можно выбрать только автомобиль из своего профиля.")
        else:
            self.selected_registered_vehicle = registered_vehicle
        return cleaned_data

    def save(self, commit=True):
        source = self.selected_registered_vehicle
        vehicle = Vehicle(
            owner=source.driver,
            owner_name=source.owner_name,
            brand=source.brand,
            model=source.model,
            year=source.year,
            license_plate=source.license_plate,
            vin=source.vin,
            insurance_policy=source.insurance_policy,
        )
        if commit:
            vehicle.save()
        return vehicle


class DamageForm(BootstrapFormMixin, forms.ModelForm):
    vehicle = forms.ModelChoiceField(label="Автомобиль", queryset=Vehicle.objects.none())

    class Meta:
        model = Damage
        fields = ("vehicle", "damage_area", "description", "severity")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, vehicles_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        if vehicles_queryset is not None:
            self.fields["vehicle"].queryset = vehicles_queryset
        self.apply_bootstrap()


class AccidentPhotoForm(BootstrapFormMixin, forms.ModelForm):
    vehicle = forms.ModelChoiceField(label="Автомобиль", queryset=Vehicle.objects.none(), required=False)

    class Meta:
        model = AccidentPhoto
        fields = ("vehicle", "image", "description")

    def __init__(self, *args, vehicles_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        if vehicles_queryset is not None:
            self.fields["vehicle"].queryset = vehicles_queryset
        self.apply_bootstrap()


class WitnessCodeForm(BootstrapFormMixin, forms.Form):
    access_code = forms.CharField(label="Код доступа", max_length=8)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["access_code"].widget.attrs.update({"placeholder": "Например, A1B2C3D4"})
        self.apply_bootstrap()

    def clean_access_code(self):
        return self.cleaned_data["access_code"].strip().upper()


class WitnessStatementForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = WitnessStatement
        fields = ("witness_full_name", "witness_phone", "statement_text", "photo")
        widgets = {
            "statement_text": forms.Textarea(attrs={"rows": 6}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()


class SubmissionConfirmForm(BootstrapFormMixin, forms.Form):
    confirm = forms.BooleanField(label="Подтверждаю отправку собранной информации в ГИБДД")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()
