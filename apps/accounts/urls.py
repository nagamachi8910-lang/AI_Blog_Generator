from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("reset-password/", views.reset_password_view, name="reset_password"),
    path("login/google/", views.google_login_initiate, name="google_login"),
    path("callback/", views.google_login_callback, name="google_callback"),
    path("logout/", views.logout_view, name="logout"),
]
