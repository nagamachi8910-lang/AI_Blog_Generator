from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch

User = get_user_model()


class DjangoSessionAuthTests(TestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.mock_claims = {
            "sub": "supabase_user_id_999",
            "email": "user999@example.com",
            "role": "authenticated",
            "app_metadata": {
                "provider": "google",
                "email_verified": True
            }
        }

    @patch("apps.accounts.views.handle_oauth_callback")
    def test_callback_first_login(self, mock_callback):
        """
        Verify that first login creates user, creates session, cycles keys, sets provider, 
        clears temporary session keys, and redirects to dashboard.
        """
        mock_callback.return_value = self.mock_claims
        
        # Setup session values simulating OAuth initiation state
        session = self.client.session
        session["supabase_code_verifier"] = "verifier_code_dummy"
        session["supabase_oauth_state"] = "oauth_state_dummy"
        session.save()
        
        # Verify no User exists initially
        self.assertEqual(User.objects.count(), 0)
        
        response = self.client.get(
            reverse("accounts:google_callback"), 
            {"code": "authcode123", "state": "oauth_state_dummy"}
        )
        
        # Verify redirect to dashboard
        self.assertRedirects(response, reverse("dashboard:dashboard"))
        
        # Verify user created in DB
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.first()
        self.assertEqual(user.supabase_user_id, "supabase_user_id_999")
        
        # Verify Django session login is active
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
        
        # Verify provider context and cleanup
        self.assertEqual(self.client.session.get("oauth_provider"), "google")
        self.assertNotIn("supabase_code_verifier", self.client.session)
        self.assertNotIn("supabase_oauth_state", self.client.session)

    @patch("apps.accounts.views.handle_oauth_callback")
    def test_callback_returning_user(self, mock_callback):
        """
        Verify that returning user is fetched and logged in without database duplicates.
        """
        mock_callback.return_value = self.mock_claims
        
        # Pre-create user in DB
        User.objects.create(
            username="existing_user",
            email="user999@example.com",
            supabase_user_id="supabase_user_id_999",
            provider="google",
            email_verified=True
        )
        self.assertEqual(User.objects.count(), 1)
        
        response = self.client.get(
            reverse("accounts:google_callback"), 
            {"code": "authcode123", "state": "oauth_state_dummy"}
        )
        
        self.assertRedirects(response, reverse("dashboard:dashboard"))
        self.assertEqual(User.objects.count(), 1)  # Still 1 user
        
        # Verify login active
        user = User.objects.first()
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    @patch("apps.accounts.views.handle_oauth_callback")
    def test_callback_redirect_next(self, mock_callback):
        """
        Verify that next redirect path is correctly honored and sanitized.
        """
        mock_callback.return_value = self.mock_claims
        
        session = self.client.session
        session["next_redirect"] = "/dashboard/blogs/create/"
        session.save()
        
        response = self.client.get(
            reverse("accounts:google_callback"), 
            {"code": "authcode123", "state": "oauth_state_dummy"}
        )
        
        # Safe URL path -> redirects user to target next page
        self.assertRedirects(response, "/dashboard/blogs/create/", target_status_code=404)
        self.assertNotIn("next_redirect", self.client.session)

    @patch("apps.accounts.views.handle_oauth_callback")
    def test_callback_redirect_next_malicious(self, mock_callback):
        """
        Verify that malicious next redirect domains are rejected and fall back to dashboard.
        """
        mock_callback.return_value = self.mock_claims
        
        session = self.client.session
        session["next_redirect"] = "http://malicious-site.com/steal-session"
        session.save()
        
        response = self.client.get(
            reverse("accounts:google_callback"), 
            {"code": "authcode123", "state": "oauth_state_dummy"}
        )
        
        # Unsafe URL -> redirects user to dashboard fallback instead
        self.assertRedirects(response, reverse("dashboard:dashboard"))

    def test_logout_view(self):
        """
        Verify that logout endpoint successfully invalidates session and redirects.
        """
        user = User.objects.create(
            username="testuser",
            email="testowner@example.com",
            supabase_user_id="sb-uuid"
        )
        self.client.force_login(user)
        
        # User is authenticated
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
        
        response = self.client.get(reverse("accounts:logout"))
        
        # Verify redirects to login
        self.assertRedirects(response, reverse("accounts:login"))
        
        # Verify session is cleaned up
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_anonymous_access_after_logout(self):
        """
        Verify that accessing user attribute after logout returns AnonymousUser.
        """
        user = User.objects.create(
            username="testuser",
            email="testowner@example.com"
        )
        self.client.force_login(user)
        
        # Before logout
        response = self.client.get(reverse("dashboard:dashboard"))
        self.assertEqual(response.status_code, 200)
        
        # Logout
        self.client.get(reverse("accounts:logout"))
        
        # Access views and verify user is AnonymousUser
        response = self.client.get(reverse("dashboard:dashboard"))
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_preserve_active_session_on_failed_callback(self):
        """
        Verify that if a user has an active session, receiving an invalid callback with error params
        doesn't terminate their logged-in session.
        """
        user = User.objects.create(
            username="loggedinuser",
            email="logged@gmail.com",
            supabase_user_id="sb-logged-id"
        )
        self.client.force_login(user)
        
        # Hit callback with error param
        response = self.client.get(reverse("accounts:google_callback"), {
            "error": "access_denied",
            "error_description": "User rejected oauth prompt"
        })
        
        # Redirects to dashboard since user is authenticated
        self.assertRedirects(response, reverse("dashboard:dashboard"))
        
        # Session user remains active
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

        # Hit callback with missing code/state param
        response2 = self.client.get(reverse("accounts:google_callback"))
        self.assertRedirects(response2, reverse("dashboard:dashboard"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
