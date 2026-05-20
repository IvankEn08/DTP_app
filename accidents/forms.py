import re

from django import forms

from users.models import DriverProfile
from .models import Accident, AccidentDriver, AccidentPhoto, Damage, Vehicle, WitnessStatement


PLATE_TRANSLATION = str.maketrans(
    {
        "A": "А",
        "B": "В",
        "E": "Е",
        "K": "К",
        "M": "М",
        "H": "Н",
        "O": "О",
        "P": "Р",
        "C": "С",
        "T": "Т",
        "Y": "У",
        "X": "Х",
    }
)
LICENSE_PLATE_RE = re.compile(r"^[АВЕКМНОРСТУХ]\d{3}[АВЕКМНОРСТУХ]{2}\d{2,3}$")
VIN_RE = re.compile(r"^[0-9A-HJ-NPR-Z]{17}$")
INSURANCE_POLICY_RE = re.compile(r"^[А-ЯЁ]{3}\d{10}$")


def normalize_plate_like_value(value):
    return re.sub(r"[\s-]+", "", value).upper().translate(PLATE_TRANSLATION)


def normalize_vin(value):
    return re.sub(r"[\s-]+", "", value).upper()


class BootstrapFormMixin:
    def apply_bootstrap(self):
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(field.widget, forms.FileInput):
                field.widget.attrs.setdefault("class", "form-control")
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


class AccidentDriverForm(BootstrapFormMixin, forms.ModelForm):
    driver = forms.ModelChoiceField(label="Второй водитель", queryset=DriverProfile.objects.none())
    role = forms.ChoiceField(label="Роль второго водителя", choices=AccidentDriver.Role.choices)

    class Meta:
        model = AccidentDriver
        fields = ("driver", "role")

    def __init__(self, *args, accident=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = DriverProfile.objects.all()
        if accident:
            queryset = queryset.exclude(accident_roles__accident=accident)
        self.fields["driver"].queryset = queryset
        self.apply_bootstrap()


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
    owner = forms.ModelChoiceField(label="Владелец", queryset=DriverProfile.objects.none())

    class Meta:
        model = Vehicle
        fields = ("owner", "brand", "model", "year", "license_plate", "vin", "insurance_policy")

    def __init__(self, *args, owners_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        if owners_queryset is not None:
            self.fields["owner"].queryset = owners_queryset
        self.fields["license_plate"].widget.attrs.update({"placeholder": "А123ВС77"})
        self.fields["vin"].widget.attrs.update({"placeholder": "17 символов без I, O, Q"})
        self.fields["insurance_policy"].widget.attrs.update({"placeholder": "ЕЕЕ1234567890"})
        self.apply_bootstrap()

    def clean_license_plate(self):
        value = normalize_plate_like_value(self.cleaned_data["license_plate"])
        if not LICENSE_PLATE_RE.match(value):
            raise forms.ValidationError("Введите госномер в формате А123ВС77 или А123ВС777. Допустимы буквы А, В, Е, К, М, Н, О, Р, С, Т, У, Х.")
        return value

    def clean_vin(self):
        value = normalize_vin(self.cleaned_data["vin"])
        if not VIN_RE.match(value):
            raise forms.ValidationError("VIN должен состоять из 17 латинских букв и цифр без I, O, Q.")
        return value

    def clean_insurance_policy(self):
        value = normalize_plate_like_value(self.cleaned_data["insurance_policy"])
        if not INSURANCE_POLICY_RE.match(value):
            raise forms.ValidationError("Введите полис ОСАГО в формате: 3 буквы серии и 10 цифр номера, например ЕЕЕ1234567890.")
        return value


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
