from django.urls import path

from . import views


app_name = "accidents"

urlpatterns = [
    path("", views.home, name="home"),
    path("accidents/", views.accident_list, name="accident_list"),
    path("gibdd/accidents/", views.gibdd_accident_list, name="gibdd_list"),
    path("accidents/create/", views.accident_create, name="create"),
    path("accidents/<int:pk>/", views.accident_detail, name="detail"),
    path("accidents/<int:pk>/edit/", views.accident_edit, name="edit"),
    path("accidents/<int:pk>/delete/", views.accident_delete, name="delete"),
    path("accidents/<int:pk>/drivers/add/", views.accident_driver_add, name="driver_add"),
    path("accidents/<int:pk>/comment/", views.driver_comment_edit, name="driver_comment_edit"),
    path("accidents/<int:pk>/ready/toggle/", views.driver_ready_toggle, name="driver_ready_toggle"),
    path("accidents/<int:pk>/vehicles/add/", views.vehicle_add, name="vehicle_add"),
    path("accidents/<int:pk>/damages/add/", views.damage_add, name="damage_add"),
    path("accidents/<int:pk>/photos/add/", views.photo_add, name="photo_add"),
    path("accidents/<int:pk>/submit/confirm/", views.submit_confirm, name="submit_confirm"),
    path("accidents/<int:pk>/submit/success/", views.submit_success, name="submit_success"),
    path("witness/", views.witness_code, name="witness_code"),
    path("witness/<str:access_code>/statement/", views.witness_statement, name="witness_statement"),
    path("witness/success/", views.witness_success, name="witness_success"),
]
