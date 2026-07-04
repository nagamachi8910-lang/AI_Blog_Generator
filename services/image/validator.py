from .provider import ImageResponse


class ImageValidator:
    @staticmethod
    def validate_image_data(response: ImageResponse) -> None:
        """
        Validates that the generated image bytes in the Response are non-empty and
        comply with standard PNG or JPEG image file header structures.
        """
        if not response or not response.image_bytes:
            raise ValueError("Invalid image response: No image bytes present.")

        image_bytes = response.image_bytes
        
        # PNG header check: \x89PNG\r\n\x1a\n
        is_png = image_bytes.startswith(b'\x89PNG\r\n\x1a\n')
        # JPEG header check: \xff\xd8
        is_jpeg = image_bytes.startswith(b'\xff\xd8')

        if not (is_png or is_jpeg):
            raise ValueError("Invalid image format. Expected PNG or JPEG source bytes.")
