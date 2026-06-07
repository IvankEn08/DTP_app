from django.test import TestCase

from .forms import DriverRegistrationForm, DriverVehicleForm
from .models import DriverProfile, DriverVehicle
from .vehicle_validation import clean_insurance_policy_value, clean_license_plate_value, clean_vin_value


class VehicleValidationTests(TestCase):
    def test_license_plate_normalization_accepts_valid_russian_plate(self):
        self.assertEqual(clean_license_plate_value("а123вс77"), "А123ВС77")

    def test_license_plate_normalization_converts_latin_lookalikes(self):
        self.assertEqual(clean_license_plate_value("A777MP777"), "А777МР777")

    def test_vin_validation_rejects_forbidden_letters(self):
        with self.assertRaisesMessage(Exception, "VIN должен состоять"):
            clean_vin_value("XTA210990Y12345I7")

    def test_insurance_policy_validation_accepts_series_and_number(self):
        self.assertEqual(clean_insurance_policy_value("xxx9876543210"), "ХХХ9876543210")


class DriverRegistrationFormTests(TestCase):
    def test_registration_form_creates_user_profile_and_first_vehicle(self):
        form = DriverRegistrationForm(
            data={
                "username": "ivanov",
                "full_name": "Иванов Иван Иванович",
                "phone": "+79000000000",
                "driver_license_number": "7712345678",
                "vehicle_owner_name": "Иванов Иван Иванович",
                "vehicle_brand": "Lada",
                "vehicle_model": "Vesta",
                "vehicle_year": 2022,
                "vehicle_license_plate": "А123ВС77",
                "vehicle_vin": "XTA210990Y1234567",
                "vehicle_insurance_policy": "ЕЕЕ1234567890",
                "password1": "StrongPass123",
                "password2": "StrongPass123",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()

        profile = DriverProfile.objects.get(user=user)
        vehicle = DriverVehicle.objects.get(driver=profile)
        self.assertEqual(profile.full_name, "Иванов Иван Иванович")
        self.assertEqual(vehicle.license_plate, "А123ВС77")
        self.assertEqual(vehicle.vin, "XTA210990Y1234567")
        self.assertEqual(vehicle.insurance_policy, "ЕЕЕ1234567890")

    def test_driver_vehicle_form_rejects_invalid_vin(self):
        form = DriverVehicleForm(
            data={
                "owner_name": "Петров Пётр Петрович",
                "brand": "Toyota",
                "model": "Camry",
                "year": 2020,
                "license_plate": "В456КЕ799",
                "vin": "JTNB11HK5K30234I6",
                "insurance_policy": "ХХХ9876543210",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("vin", form.errors)
