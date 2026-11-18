from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register_student, name="register_student"),
    path("attendance/", views.take_attendance, name="take_attendance"),
    path("database/", views.view_database, name="view_database"),
]
