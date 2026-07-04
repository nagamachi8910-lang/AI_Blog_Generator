from django.test import TestCase
from django.contrib.auth import get_user_model
from services.auth.identity import extract_identity
from services.auth.user_sync import synchronize_user

User = get_user_model()


class UserSyncTests(TestCase):
    def setUp(self):
        super().setUp()
        self.mock_claims = {
            "sub": "supabase-uuid-1111",
            "email": "user1@example.com",
            "role": "authenticated",
            "app_metadata": {
                "provider": "google",
                "email_verified": True
            },
            "user_metadata": {}
        }
        
    def test_extract_identity_valid(self):
        """
        Test that extract_identity correctly pulls and normalizes JWT claims.
        """
        identity = extract_identity(self.mock_claims)
        self.assertEqual(identity["supabase_user_id"], "supabase-uuid-1111")
        self.assertEqual(identity["email"], "user1@example.com")
        self.assertEqual(identity["provider"], "google")
        self.assertEqual(identity["role"], "authenticated")
        self.assertTrue(identity["email_verified"])

    def test_first_login_creates_user(self):
        """
        Test that running sync for a first-time user creates a Django User with matching fields.
        """
        identity = extract_identity(self.mock_claims)
        
        # Verify no User exists initially
        self.assertEqual(User.objects.count(), 0)
        
        user = synchronize_user(identity)
        
        # Verify user is created in database
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(user.supabase_user_id, "supabase-uuid-1111")
        self.assertEqual(user.email, "user1@example.com")
        self.assertEqual(user.provider, "google")
        self.assertEqual(user.role, "authenticated")
        self.assertTrue(user.email_verified)
        self.assertFalse(user.has_usable_password())

    def test_returning_user_logs_in(self):
        """
        Test that a returning user matching supabase_user_id is fetched and updated without creating duplicate User.
        """
        identity = extract_identity(self.mock_claims)
        
        user1 = synchronize_user(identity)
        self.assertEqual(User.objects.count(), 1)
        
        # Sync again (returning user login)
        user2 = synchronize_user(identity)
        
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(user1.id, user2.id)

    def test_changed_email_metadata_updates(self):
        """
        Test that updates in claims email/metadata sync to the local User object.
        """
        identity = extract_identity(self.mock_claims)
        user = synchronize_user(identity)
        
        self.assertEqual(user.email, "user1@example.com")
        self.assertEqual(user.role, "authenticated")
        
        # Modify claims and sync again
        updated_claims = self.mock_claims.copy()
        updated_claims["email"] = "new_email@example.com"
        updated_claims["role"] = "super-role"
        updated_claims["app_metadata"] = {
            "provider": "github",
            "email_verified": False
        }
        
        new_identity = extract_identity(updated_claims)
        updated_user = synchronize_user(new_identity)
        
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(updated_user.email, "new_email@example.com")
        self.assertEqual(updated_user.role, "super-role")
        self.assertEqual(updated_user.provider, "github")
        self.assertFalse(updated_user.email_verified)

    def test_fallback_match_by_email(self):
        """
        Test that if a Django user already exists with the email (e.g. created by other administration channels),
        synchronization links the Supabase user ID instead of making a duplicate user.
        """
        # Create pre-existing Django user
        pre_existing = User.objects.create(
            username="existing_user",
            email="user1@example.com",
            supabase_user_id=None
        )
        self.assertEqual(User.objects.count(), 1)
        
        identity = extract_identity(self.mock_claims)
        user = synchronize_user(identity)
        
        # Asserts no duplicate user created
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(user.id, pre_existing.id)
        # Asserts supabase ID linked
        self.assertEqual(user.supabase_user_id, "supabase-uuid-1111")

    def test_missing_optional_claims(self):
        """
        Test that synchronization handles claims with missing optional parameters gracefully.
        """
        minimal_claims = {
            "sub": "supabase-uuid-2222"
        }
        identity = extract_identity(minimal_claims)
        
        user = synchronize_user(identity)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(user.supabase_user_id, "supabase-uuid-2222")
        self.assertEqual(user.email, "")
        self.assertEqual(user.provider, "email")
        self.assertEqual(user.role, "authenticated")
        self.assertFalse(user.email_verified)
