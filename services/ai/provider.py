from abc import ABC, abstractmethod
from .validator import validate_response_structure


class GenerationResponse(str):
    """
    A structured representation of an AI content generation response.
    Inherits from str to maintain compatibility with the existing parser and pipeline.
    """
    def __new__(cls, text: str, provider: str = None, model: str = None):
        obj = super().__new__(cls, text)
        obj._text = text
        obj.provider = provider
        obj.model = model
        return obj

    @property
    def text(self) -> str:
        return self._text


class AIProvider(ABC):
    @abstractmethod
    def generate_content(self, prompt, model: str = None) -> GenerationResponse:
        """
        Sends the prompt structure to the AI provider and returns a GenerationResponse.
        """
        pass


class DummyProvider(AIProvider):
    def generate_content(self, prompt, model: str = None) -> GenerationResponse:
        """
        Simulated provider returning structured blog JSON.
        """
        mock_json_str = """{
  "schema_version": "1.0.0",
  "title": "Mock Title: AI Design and Architecture",
  "summary": "A Mock Summary covering architectural principles and modular structures.",
  "sections": [
    {
      "id": "sec-uuid-1",
      "order": 1,
      "type": "heading",
      "heading": "1. Core Principles",
      "content": "Modular clean boundaries are simpler to maintain.",
      "metadata": {}
    },
    {
      "id": "sec-uuid-2",
      "order": 2,
      "type": "paragraph",
      "heading": "Service Architecture",
      "content": "Business logic should decouple completely from views, databases, and external libraries.",
      "metadata": {}
    },
    {
      "id": "sec-uuid-3",
      "order": 3,
      "type": "summary",
      "heading": "Conclusion",
      "content": "Testing boundaries and clean models are foundational pillars.",
      "metadata": {}
    }
  ]
}"""
        validate_response_structure(mock_json_str)
        return GenerationResponse(mock_json_str, provider="dummy", model=model or "default-mock")


def get_provider(provider_name: str) -> AIProvider:
    """
    Factory function returning the configured provider implementation.
    """
    provider_name = (provider_name or "").lower().strip()
    if provider_name in ("dummy", "", "mock"):
        return DummyProvider()
    elif provider_name == "gemini":
        from .gemini_provider import GeminiProvider
        return GeminiProvider()
        
    raise ValueError(f"AI Provider '{provider_name}' is not implemented.")
