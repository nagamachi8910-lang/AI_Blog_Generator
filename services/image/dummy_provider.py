from .provider import ImageProvider, ImagePrompt, ImageResponse


class DummyImageProvider(ImageProvider):
    def generate_image(self, prompt: ImagePrompt, model: str = None) -> ImageResponse:
        """
        Generates simulated image bytes (a valid 1x1 pixel PNG).
        """
        # Standard 1x1 transparent PNG byte contents
        dummy_png_bytes = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4'
            b'\x00\x00\x00\rIDATx\x9cc`\x00\x01\x00\x00\x02\x00\x01e\x81\xd0\xbb\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        return ImageResponse(
            image_bytes=dummy_png_bytes,
            provider="dummy",
            model=model or "dummy-stable-diffusion"
        )
