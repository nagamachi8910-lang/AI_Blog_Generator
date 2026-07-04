import json
from django.test import TestCase, override_settings
from unittest.mock import patch, MagicMock
from google.genai.errors import APIError
from services.ai.prompt_builder import PromptBuilder
from services.ai.gemini_provider import GeminiProvider
from services.ai.provider import GenerationResponse


@override_settings(
    GEMINI_API_KEY="mocked-api-key",
    GEMINI_DEFAULT_MODEL="gemini-1.5-flash",
    GEMINI_MAX_RETRIES=3,
    GEMINI_RETRY_DELAY=0.1,
    GEMINI_TIMEOUT=10.0
)
class GeminiProviderTests(TestCase):
    def setUp(self):
        super().setUp()
        self.provider = GeminiProvider()
        self.prompt = PromptBuilder.build_blog_prompt(
            topic="Testing",
            tone="Technical",
            title="A title mock"
        )
        self.mock_success_text = """{
  "schema_version": "1.0.0",
  "title": "Mock Title: AI Design and Architecture",
  "summary": "A Mock Summary covering architectural principles and modular structures.",
  "sections": [
    {
      "id": "sec-1",
      "order": 1,
      "type": "heading",
      "heading": "1. Core Principles",
      "content": "Modular clean boundaries are simpler to maintain.",
      "metadata": {}
    },
    {
      "id": "sec-2",
      "order": 2,
      "type": "paragraph",
      "heading": "Service Architecture",
      "content": "Business logic should decouple completely from views, databases, and external libraries.",
      "metadata": {}
    },
    {
      "id": "sec-3",
      "order": 3,
      "type": "summary",
      "heading": "Conclusion",
      "content": "Testing boundaries and clean models are foundational...",
      "metadata": {}
    }
  ]
}"""

    @patch("services.ai.gemini_provider.genai.Client")
    def test_generate_content_success(self, mock_client_class):
        """
        Verify that a successful Client.models.generate_content execution yields a GenerationResponse
        with correct attributes.
        """
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = self.mock_success_text
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        res = self.provider.generate_content(self.prompt)
        
        self.assertIsInstance(res, GenerationResponse)
        self.assertEqual(res.provider, "gemini")
        self.assertEqual(res.model, "gemini-1.5-flash")
        self.assertEqual(res.text, self.mock_success_text)
        
        mock_client.models.generate_content.assert_called_once()

    @patch("services.ai.gemini_provider.time.sleep")
    @patch("services.ai.gemini_provider.genai.Client")
    def test_generate_content_rate_limit_and_recover(self, mock_client_class, mock_sleep):
        """
        Verify that rate-limit errors (HTTP 429) hit sleep backoff logic and succeed on subsequent attempt.
        """
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_err = APIError(code=429, response_json={"message": "Rate limit exceeded"})
        mock_response = MagicMock()
        mock_response.text = self.mock_success_text
        mock_client.models.generate_content.side_effect = [mock_err, mock_response]

        res = self.provider.generate_content(self.prompt)
        
        self.assertEqual(res.text, self.mock_success_text)
        self.assertEqual(mock_client.models.generate_content.call_count, 2)
        mock_sleep.assert_called_once_with(0.1)

    @patch("services.ai.gemini_provider.genai.Client")
    def test_generate_content_invalid_api_key_fails_immediately(self, mock_client_class):
        """
        Verify credentials error (HTTP 400 or 403) aborts immediately.
        """
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_err = APIError(code=400, response_json={"message": "API key not valid"})
        mock_client.models.generate_content.side_effect = mock_err

        with self.assertRaises(ValueError) as ctx:
            self.provider.generate_content(self.prompt)
            
        self.assertIn("Invalid Gemini API key", str(ctx.exception))
        mock_client.models.generate_content.assert_called_once()

    @patch("services.ai.gemini_provider.genai.Client")
    def test_generate_content_empty_response_fails(self, mock_client_class):
        """
        Verify that empty response text raises ValueError.
        """
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = ""
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        with self.assertRaises(ValueError) as ctx:
            self.provider.generate_content(self.prompt)
            
        self.assertIn("Empty response", str(ctx.exception))

    @patch("services.ai.gemini_provider.genai.Client")
    def test_generate_content_malformed_structure_fails(self, mock_client_class):
        """
        Verify that structural validation fails when top-level keys are missing.
        """
        mock_client = MagicMock()
        mock_response = MagicMock()
        # Invalid schema version JSON field
        mock_response.text = json.dumps({
            "schema_version": "2.0.0",
            "title": "Clean Code",
            "summary": "Best practices",
            "sections": []
        })
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        with self.assertRaises(ValueError) as ctx:
            self.provider.generate_content(self.prompt)
            
        self.assertIn("Unsupported schema version: 2.0.0", str(ctx.exception))

    @override_settings(GEMINI_API_KEY=None)
    def test_missing_api_key_configuration(self):
        """
        Verify missing API Key raises ValueError directly.
        """
        provider = GeminiProvider()
        with self.assertRaises(ValueError) as ctx:
            provider.generate_content(self.prompt)
        self.assertIn("API key is not configured", str(ctx.exception))
