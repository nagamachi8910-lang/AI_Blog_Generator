import logging
from apps.blogs.models import BlogImage
from .factory import get_image_provider
from .selector import ImageSelector
from .prompt_builder import ImagePromptBuilder
from .storage import ImageStorage
from .validator import ImageValidator

logger = logging.getLogger(__name__)


class ImagePipeline:
    def __init__(self, provider_name: str = "dummy"):
        self.provider = get_image_provider(provider_name)
        self.selector = ImageSelector()
        self.prompt_builder = ImagePromptBuilder()
        self.storage = ImageStorage()
        self.validator = ImageValidator()

    def generate_images_for_blog(self, blog, model: str = None) -> list:
        """
        Orchestration pipeline: selects sections, constructs prompts, calls providers,
        validates content signatures, and saves outputs to media storage.
        If a section fails generation, continues formatting others without throwing exceptions.
        """
        sections_needing_images = self.selector.select_sections_for_images(blog)
        created_images = []

        for section in sections_needing_images:
            try:
                # 1. Compile prompt object
                prompt_obj = self.prompt_builder.build_prompt(
                    blog_title=blog.title,
                    blog_topic=blog.topic,
                    section_heading=section.heading,
                    section_content=section.content,
                    section_type=section.section_type
                )
                
                # 2. Invoke image model
                image_response = self.provider.generate_image(prompt_obj, model)
                
                # 3. Validate image data header structures
                self.validator.validate_image_data(image_response)
                
                # 4. Save to files storage
                filename = f"blog_{blog.id}_sec_{section.id}.png"
                saved_path = self.storage.save_image(filename, image_response)
                
                # 5. Create BlogImage database record
                blog_image = BlogImage.objects.create(
                    blog=blog,
                    section=section,
                    image=saved_path,
                    prompt=prompt_obj.prompt_text,
                    provider=image_response.provider,
                    model=image_response.model
                )
                created_images.append(blog_image)
                
            except Exception as e:
                # Recover silently for other sections
                logger.error(
                    f"Image generation failed for section '{section.id}' in blog '{blog.id}': {str(e)}"
                )
                continue
                
        return created_images
