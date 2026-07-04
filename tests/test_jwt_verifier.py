import time
import jwt
from django.test import TestCase, override_settings
from unittest.mock import patch
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm
from services.auth.jwt_verifier import verify_access_token


class JWTVerifierTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Generate RSA keypair for mock token generation
        cls.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        # Build matching JWK structure
        public_key = cls.private_key.public_key()
        import json
        cls.jwk = json.loads(RSAAlgorithm.to_jwk(public_key))
        cls.jwk.update({
            "kid": "test-kid",
            "alg": "RS256",
            "use": "sig",
            "kty": "RSA"
        })
        cls.jwks_data = {
            "keys": [cls.jwk]
        }
        
    def setUp(self):
        super().setUp()
        # Mock network fetch of JWKS data
        self.fetch_patcher = patch("jwt.jwks_client.PyJWKClient.fetch_data", return_value=self.jwks_data)
        self.mock_fetch = self.fetch_patcher.start()
        
    def tearDown(self):
        self.fetch_patcher.stop()
        super().tearDown()
        
    def generate_token(self, headers=None, payload=None, sign_key=None, algorithm="RS256"):
        """
        Helper method to generate signed JWTs for testing.
        """
        token_headers = {"kid": "test-kid"}
        if headers:
            token_headers.update(headers)
            
        token_payload = {
            "iss": "https://szzyrbpekghxnlxaijwd.supabase.co/auth/v1",
            "aud": "authenticated",
            "sub": "user-uuid-1234",
            "email": "test@example.com",
            "role": "authenticated",
            "iat": int(time.time()),
            "exp": int(time.time()) + 300
        }
        if payload:
            token_payload.update(payload)
            
        key_to_use = sign_key or self.private_key
        return jwt.encode(token_payload, key_to_use, algorithm=algorithm, headers=token_headers)

    @override_settings(
        SUPABASE_URL="https://szzyrbpekghxnlxaijwd.supabase.co",
        SUPABASE_JWKS_URL="https://example.com/jwks.json",
        SUPABASE_JWKS_CACHE_TIMEOUT=300,
        SUPABASE_JWT_LEEWAY=10
    )
    def test_verify_valid_token(self):
        """
        Test that a valid token parses and returns verified claims successfully.
        """
        token = self.generate_token()
        claims = verify_access_token(token)
        
        self.assertEqual(claims.get("sub"), "user-uuid-1234")
        self.assertEqual(claims.get("email"), "test@example.com")
        self.assertEqual(claims.get("role"), "authenticated")
        self.assertEqual(claims.get("iss"), "https://szzyrbpekghxnlxaijwd.supabase.co/auth/v1")
        self.assertEqual(claims.get("aud"), "authenticated")

    @override_settings(
        SUPABASE_URL="https://szzyrbpekghxnlxaijwd.supabase.co",
        SUPABASE_JWKS_URL="https://example.com/jwks.json",
        SUPABASE_JWKS_CACHE_TIMEOUT=300,
        SUPABASE_JWT_LEEWAY=5
    )
    def test_verify_expired_token(self):
        """
        Test that an expired token is correctly rejected.
        """
        token = self.generate_token(payload={"exp": int(time.time()) - 10})
        
        with self.assertRaises(ValueError) as ctx:
            verify_access_token(token)
        self.assertIn("expired", str(ctx.exception).lower())

    @override_settings(
        SUPABASE_URL="https://szzyrbpekghxnlxaijwd.supabase.co",
        SUPABASE_JWKS_URL="https://example.com/jwks.json",
    )
    def test_verify_invalid_signature(self):
        """
        Test that a token signed with an invalid/mismatched key is rejected.
        """
        different_private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        token = self.generate_token(sign_key=different_private_key)
        
        with self.assertRaises(ValueError) as ctx:
            verify_access_token(token)
        self.assertIn("signature", str(ctx.exception).lower())

    @override_settings(
        SUPABASE_URL="https://szzyrbpekghxnlxaijwd.supabase.co",
        SUPABASE_JWKS_URL="https://example.com/jwks.json",
    )
    def test_verify_malformed_token(self):
        """
        Test that a malformed token structure is cleanly caught and rejected.
        """
        invalid_token = "not.a.jwt.token"
        with self.assertRaises(ValueError) as ctx:
            verify_access_token(invalid_token)
        self.assertIn("malformed", str(ctx.exception).lower())

    @override_settings(
        SUPABASE_URL="https://szzyrbpekghxnlxaijwd.supabase.co",
        SUPABASE_JWKS_URL="https://example.com/jwks.json",
    )
    def test_verify_issuer_failure(self):
        """
        Test that a token with an invalid/mismatched issuer is rejected.
        """
        token = self.generate_token(payload={"iss": "https://wrong-issuer.com"})
        with self.assertRaises(ValueError) as ctx:
            verify_access_token(token)
        self.assertIn("issuer", str(ctx.exception).lower())

    @override_settings(
        SUPABASE_URL="https://szzyrbpekghxnlxaijwd.supabase.co",
        SUPABASE_JWKS_URL="https://example.com/jwks.json",
    )
    def test_verify_audience_failure(self):
        """
        Test that a token with an invalid audience is rejected.
        """
        token = self.generate_token(payload={"aud": "wrong-audience"})
        with self.assertRaises(ValueError) as ctx:
            verify_access_token(token)
        self.assertIn("audience", str(ctx.exception).lower())

    @override_settings(
        SUPABASE_URL="https://szzyrbpekghxnlxaijwd.supabase.co",
        SUPABASE_JWKS_URL="https://example.com/jwks.json",
    )
    def test_verify_unsupported_algorithm(self):
        """
        Test that tokens signed with an unsupported algorithm (e.g. HS256) are rejected.
        """
        token = jwt.encode(
            {
                "iss": "https://szzyrbpekghxnlxaijwd.supabase.co/auth/v1",
                "aud": "authenticated",
                "exp": int(time.time()) + 300,
                "iat": int(time.time()),
                "sub": "test"
            },
            "fake-secret-key-12345",
            algorithm="HS256",
            headers={"kid": "test-kid"}
        )
        with self.assertRaises(ValueError) as ctx:
            verify_access_token(token)
        self.assertTrue(
            "algorithm" in str(ctx.exception).lower() or 
            "signature" in str(ctx.exception).lower() or
            "failed" in str(ctx.exception).lower()
        )

    @override_settings(
        SUPABASE_URL="https://szzyrbpekghxnlxaijwd.supabase.co",
        SUPABASE_JWKS_URL="https://example.com/jwks.json",
    )
    def test_verify_jwks_retrieval_failure(self):
        """
        Test that an unavailable JWKS endpoint generates a proper error response.
        """
        # Force fetch_data to raise a network/client error
        self.mock_fetch.side_effect = jwt.PyJWKClientError("Connection timed out.")
        token = self.generate_token()
        
        with self.assertRaises(ValueError) as ctx:
            verify_access_token(token)
        self.assertIn("jwks endpoint", str(ctx.exception).lower())
