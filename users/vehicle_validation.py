import re

from django import forms


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


def clean_license_plate_value(value):
    normalized = normalize_plate_like_value(value)
    if not LICENSE_PLATE_RE.match(normalized):
        raise forms.ValidationError("Введите госномер в формате А123ВС77 или А123ВС777. Допустимы буквы А, В, Е, К, М, Н, О, Р, С, Т, У, Х.")
    return normalized


def clean_vin_value(value):
    normalized = normalize_vin(value)
    if not VIN_RE.match(normalized):
        raise forms.ValidationError("VIN должен состоять из 17 латинских букв и цифр без I, O, Q.")
    return normalized


def clean_insurance_policy_value(value):
    normalized = normalize_plate_like_value(value)
    if not INSURANCE_POLICY_RE.match(normalized):
        raise forms.ValidationError("Введите полис ОСАГО в формате: 3 буквы серии и 10 цифр номера, например ЕЕЕ1234567890.")
    return normalized
