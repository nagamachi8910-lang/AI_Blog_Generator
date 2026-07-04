from django.urls import path
from . import views

app_name = "generator"

urlpatterns = [
    path("", views.generator_view, name="generator"),
    path("process/", views.process_view, name="process"),
    path("api/generate/", views.api_generate_view, name="api_generate"),
]
