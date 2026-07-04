from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    supabase_user_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Unique user identifier from Supabase Auth"
    )
    provider = models.CharField(
        max_length=50,
        blank=True,
        help_text="OAuth provider or login method (e.g. google, email)"
    )
    role = models.CharField(
        max_length=50,
        blank=True,
        help_text="Supabase user role (e.g. authenticated)"
    )
    email_verified = models.BooleanField(
        default=False,
        help_text="Verification status of the email"
    )

    def __str__(self):
        return self.email or self.username
