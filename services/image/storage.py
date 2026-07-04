import os
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .provider import ImageResponse


class ImageStorage:
    def save_image(self, filename: str, response: ImageResponse) -> str:
        """
        Saves raw image bytes from the ImageResponse to MEDIA_ROOT under 'blog_images/'
        and returns the stored file path.
        """
        # Save relative to MEDIA_ROOT (e.g. media/blog_images/{filename})
        relative_path = os.path.join("blog_images", filename)
        content_file = ContentFile(response.image_bytes)
        saved_path = default_storage.save(relative_path, content_file)
        return saved_path
