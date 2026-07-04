from .provider import ImageProvider
from .dummy_provider import DummyImageProvider


def get_image_provider(provider_name: str) -> ImageProvider:
    """
    Factory function returning the desired ImageProvider instance.
    """
    name = (provider_name or "").lower().strip()
    if name in ("dummy", "", "mock"):
        return DummyImageProvider()
        
    raise ValueError(f"Image Provider '{provider_name}' is not configured/implemented.")
