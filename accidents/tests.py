from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from users.models import DriverProfile, DriverVehicle
from .forms import AccidentCreateForm, AccidentPhotoForm, VehicleForm
from .models import Accident, AccidentDriver, AccidentPhoto, SubmissionLog, Vehicle, WitnessStatement
from .views import accident_drivers_are_ready, submit_blocker_message, user_can_submit


class AccidentTestMixin:
    def create_driver(self, username, full_name, license_number):
        user = User.objects.create_user(username=username, password="StrongPass123")
        profile = DriverProfile.objects.create(
            user=user,
            full_name=full_name,
            phone="+79000000000",
            driver_license_number=license_number,
        )
        DriverVehicle.objects.create(
            driver=profile,
            owner_name=full_name,
            brand="Lada",
            model="Vesta",
            year=2022,
            license_plate="А123ВС77",
            vin="XTA210990Y1234567",
            insurance_policy="ЕЕЕ1234567890",
        )
        return user, profile

    def create_accident(self, creator, creator_profile):
        accident = Accident.objects.create(
            title="Тестовое ДТП",
            accident_date=timezone.now(),
            location="Москва, Тверская 1",
            created_by=creator,
        )
        AccidentDriver.objects.create(
            accident=accident,
            driver=creator_profile,
            role=AccidentDriver.Role.VICTIM,
            comment="Комментарий первого водителя",
        )
        return accident


class AccidentModelTests(AccidentTestMixin, TestCase):
    def test_accident_generates_witness_and_driver_join_codes(self):
        user, profile = self.create_driver("ivanov", "Иванов Иван Иванович", "7712345678")
        accident = self.create_accident(user, profile)

        self.assertEqual(len(accident.access_code), 8)
        self.assertEqual(len(accident.driver_join_code), 8)
        self.assertNotEqual(accident.access_code, accident.driver_join_code)


class AccidentCreateViewTests(AccidentTestMixin, TestCase):
    def test_create_accident_adds_creator_as_first_participant_without_vehicle(self):
        user, profile = self.create_driver("ivanov", "Иванов Иван Иванович", "7712345678")
        self.client.force_login(user)

        response = self.client.post(
            reverse("accidents:create"),
            data={
                "title": "Царапина на двери",
                "accident_date": "2026-05-29T12:30",
                "location": "Комсомольский проспект 192",
                "driver_comment": "Двигался по правой полосе.",
            },
        )

        accident = Accident.objects.get(title="Царапина на двери")
        self.assertRedirects(response, reverse("accidents:detail", args=[accident.pk]))
        self.assertTrue(accident.drivers.filter(driver=profile).exists())
        self.assertEqual(accident.vehicles.count(), 0)

    def test_accident_create_form_contains_only_short_accident_fields(self):
        form = AccidentCreateForm()

        self.assertEqual(
            list(form.fields.keys()),
            ["title", "accident_date", "location", "driver_comment"],
        )


class VehicleFormTests(AccidentTestMixin, TestCase):
    def test_vehicle_form_rejects_vehicle_from_another_profile(self):
        _, profile = self.create_driver("ivanov", "Иванов Иван Иванович", "7712345678")
        _, other_profile = self.create_driver("petrov", "Петров Пётр Петрович", "7712345679")
        other_vehicle = other_profile.registered_vehicles.first()

        form = VehicleForm(
            owner_profile=profile,
            data={"registered_vehicle": other_vehicle.pk},
        )

        self.assertFalse(form.is_valid())
        self.assertIn("registered_vehicle", form.errors)

    def test_vehicle_form_can_copy_registered_vehicle(self):
        user, profile = self.create_driver("ivanov", "Иванов Иван Иванович", "7712345678")
        accident = self.create_accident(user, profile)
        registered_vehicle = profile.registered_vehicles.first()

        form = VehicleForm(
            owner_profile=profile,
            data={"registered_vehicle": registered_vehicle.pk},
        )

        self.assertTrue(form.is_valid(), form.errors)
        vehicle = form.save(commit=False)
        vehicle.accident = accident
        vehicle.save()

        self.assertEqual(vehicle.owner, profile)
        self.assertEqual(vehicle.license_plate, registered_vehicle.license_plate)
        self.assertEqual(vehicle.owner_name, registered_vehicle.owner_name)


class PhotoFormTests(AccidentTestMixin, TestCase):
    def test_accident_photo_form_accepts_image(self):
        user, profile = self.create_driver("ivanov", "Иванов Иван Иванович", "7712345678")
        accident = self.create_accident(user, profile)
        vehicle = Vehicle.objects.create(
            accident=accident,
            owner=profile,
            owner_name=profile.full_name,
            brand="Lada",
            model="Vesta",
            year=2022,
            license_plate="А123ВС77",
            vin="XTA210990Y1234567",
            insurance_policy="ЕЕЕ1234567890",
        )
        image = SimpleUploadedFile(
            "damage.gif",
            b"GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
            content_type="image/gif",
        )

        form = AccidentPhotoForm(
            data={"vehicle": vehicle.pk, "description": "Передний бампер"},
            files={"image": image},
            vehicles_queryset=Vehicle.objects.filter(accident=accident, owner=profile),
        )

        self.assertTrue(form.is_valid(), form.errors)


class DriverJoinWorkflowTests(AccidentTestMixin, TestCase):
    def test_second_driver_joins_accident_by_driver_code(self):
        user1, profile1 = self.create_driver("ivanov", "Иванов Иван Иванович", "7712345678")
        user2, profile2 = self.create_driver("petrov", "Петров Пётр Петрович", "7712345679")
        accident = self.create_accident(user1, profile1)
        accident.second_driver_role = AccidentDriver.Role.RESPONSIBLE
        accident.save(update_fields=["second_driver_role"])
        self.client.force_login(user2)

        response = self.client.post(
            reverse("accidents:driver_join"),
            data={"driver_join_code": accident.driver_join_code},
        )

        self.assertRedirects(response, reverse("accidents:detail", args=[accident.pk]))
        self.assertTrue(accident.drivers.filter(driver=profile2, role=AccidentDriver.Role.RESPONSIBLE).exists())
        self.assertTrue(accident.drivers.filter(driver=profile1, role=AccidentDriver.Role.VICTIM).exists())

    def test_wrong_driver_join_code_does_not_add_participant(self):
        user1, profile1 = self.create_driver("ivanov", "Иванов Иван Иванович", "7712345678")
        user2, _ = self.create_driver("petrov", "Петров Пётр Петрович", "7712345679")
        accident = self.create_accident(user1, profile1)
        self.client.force_login(user2)

        response = self.client.post(reverse("accidents:driver_join"), data={"driver_join_code": "BADCODE1"})

        self.assertRedirects(response, reverse("accidents:accident_list"))
        self.assertEqual(accident.drivers.count(), 1)


class AccessAndSubmissionTests(AccidentTestMixin, TestCase):
    def prepare_two_driver_accident(self):
        user1, profile1 = self.create_driver("ivanov", "Иванов Иван Иванович", "7712345678")
        user2, profile2 = self.create_driver("petrov", "Петров Пётр Петрович", "7712345679")
        accident = self.create_accident(user1, profile1)
        first_participant = accident.drivers.get(driver=profile1)
        first_participant.role = AccidentDriver.Role.VICTIM
        first_participant.save(update_fields=["role"])
        AccidentDriver.objects.create(
            accident=accident,
            driver=profile2,
            role=AccidentDriver.Role.RESPONSIBLE,
            comment="Комментарий второго водителя",
        )
        return accident, user1, profile1, user2, profile2

    def test_unrelated_driver_cannot_open_accident_detail(self):
        owner, owner_profile = self.create_driver("ivanov", "Иванов Иван Иванович", "7712345678")
        stranger, _ = self.create_driver("sidorov", "Сидоров Сидор Сидорович", "7712345680")
        accident = self.create_accident(owner, owner_profile)
        self.client.force_login(stranger)

        response = self.client.get(reverse("accidents:detail", args=[accident.pk]))

        self.assertEqual(response.status_code, 403)

    def test_responsible_driver_cannot_submit_until_both_ready(self):
        accident, _, _, user2, _ = self.prepare_two_driver_accident()

        self.assertFalse(accident_drivers_are_ready(accident))
        self.assertFalse(user_can_submit(user2, accident))
        self.assertIn("подтверждения", submit_blocker_message(user2, accident))

    def test_responsible_driver_can_submit_after_both_ready(self):
        accident, _, _, user2, _ = self.prepare_two_driver_accident()
        accident.drivers.update(is_ready=True, ready_at=timezone.now())

        self.assertTrue(accident_drivers_are_ready(accident))
        self.assertTrue(user_can_submit(user2, accident))

    def test_submit_confirm_sets_submitted_at_and_creates_log(self):
        accident, _, _, user2, _ = self.prepare_two_driver_accident()
        accident.drivers.update(is_ready=True, ready_at=timezone.now())
        self.client.force_login(user2)

        response = self.client.post(
            reverse("accidents:submit_confirm", args=[accident.pk]),
            data={"confirm": "on"},
        )

        accident.refresh_from_db()
        self.assertRedirects(response, reverse("accidents:submit_success", args=[accident.pk]))
        self.assertIsNotNone(accident.submitted_at)
        self.assertEqual(SubmissionLog.objects.filter(accident=accident, submitted_by=user2).count(), 1)


class WitnessAndDashboardTests(AccidentTestMixin, TestCase):
    def test_witness_statement_is_saved_by_access_code_without_login(self):
        user, profile = self.create_driver("ivanov", "Иванов Иван Иванович", "7712345678")
        accident = self.create_accident(user, profile)

        response = self.client.post(
            reverse("accidents:witness_statement", args=[accident.access_code]),
            data={
                "witness_full_name": "Смирнов Сергей Сергеевич",
                "witness_phone": "+79001234567",
                "statement_text": "Видел момент столкновения.",
            },
        )

        self.assertRedirects(response, reverse("accidents:witness_success"))
        self.assertEqual(WitnessStatement.objects.filter(accident=accident).count(), 1)

    def test_witness_statement_can_save_photo(self):
        user, profile = self.create_driver("ivanov", "Иванов Иван Иванович", "7712345678")
        accident = self.create_accident(user, profile)
        image = SimpleUploadedFile(
            "witness.gif",
            b"GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
            content_type="image/gif",
        )

        response = self.client.post(
            reverse("accidents:witness_statement", args=[accident.access_code]),
            data={
                "witness_full_name": "Смирнов Сергей Сергеевич",
                "witness_phone": "+79001234567",
                "statement_text": "Видел момент столкновения.",
                "photo": image,
            },
        )

        self.assertRedirects(response, reverse("accidents:witness_success"))
        self.assertTrue(WitnessStatement.objects.get(accident=accident).photo)

    def test_participant_can_upload_accident_photo(self):
        user, profile = self.create_driver("ivanov", "Иванов Иван Иванович", "7712345678")
        accident = self.create_accident(user, profile)
        vehicle = Vehicle.objects.create(
            accident=accident,
            owner=profile,
            owner_name=profile.full_name,
            brand="Lada",
            model="Vesta",
            year=2022,
            license_plate="А123ВС77",
            vin="XTA210990Y1234567",
            insurance_policy="ЕЕЕ1234567890",
        )
        image = SimpleUploadedFile(
            "damage.gif",
            b"GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
            content_type="image/gif",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("accidents:photo_add", args=[accident.pk]),
            data={"vehicle": vehicle.pk, "description": "Передний бампер", "image": image},
        )

        self.assertRedirects(response, reverse("accidents:detail", args=[accident.pk]))
        self.assertEqual(AccidentPhoto.objects.filter(accident=accident).count(), 1)

    def test_gibdd_dashboard_available_only_for_staff(self):
        staff = User.objects.create_user(username="staff", password="StrongPass123", is_staff=True)
        user, _ = self.create_driver("ivanov", "Иванов Иван Иванович", "7712345678")

        self.client.force_login(user)
        forbidden_response = self.client.get(reverse("accidents:gibdd_dashboard"))
        self.assertEqual(forbidden_response.status_code, 403)

        self.client.force_login(staff)
        response = self.client.get(reverse("accidents:gibdd_dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_driver_certificate_pdf_export_returns_pdf(self):
        user, profile = self.create_driver("ivanov", "Иванов Иван Иванович", "7712345678")
        self.create_accident(user, profile)
        self.client.force_login(user)

        response = self.client.get(reverse("accidents:driver_certificate"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
