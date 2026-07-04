import os
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from apps.blogs.models import Blog, BlogSection, BlogImage
from services.image.provider import ImagePrompt, ImageResponse
from services.image.pipeline import ImagePipeline
from services.image.prompt_builder import ImagePromptBuilder
from services.image.selector import ImageSelector
from services.image.storage import ImageStorage
from services.image.validator import ImageValidator

User = get_user_model()


class ImagePipelineTests(TestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="image_author",
            email="image_author@example.com",
            password="authpassword12"
        )
        self.blog = Blog.objects.create(
            author=self.user,
            title="AI Image Automation",
            topic="Image generation",
            tone="Professional",
            status="generated"
        )
        # Create different section types
        self.sec_paragraph = BlogSection.objects.create(
            blog=self.blog,
            section_type="paragraph",
            heading="Paragraph Heading",
            content="This is section content to describe the paragraph.",
            order=1
        )
        self.sec_heading = BlogSection.objects.create(
            blog=self.blog,
            section_type="heading",
            heading="Section Heading ONLY",
            content="",
            order=2
        )
        self.sec_tip = BlogSection.objects.create(
            blog=self.blog,
            section_type="tip",
            heading="Useful Tips",
            content="Always write modular code blocks.",
            order=3
        )
        self.sec_code = BlogSection.objects.create(
            blog=self.blog,
            section_type="code",
            heading="Sample Code",
            content="print('Hello World')",
            order=4
        )

    def test_image_selector_filtered_types(self):
        """
        Verify selector selects only configured eligible section types.
        """
        selector = ImageSelector()
        sections = selector.select_sections_for_images(self.blog)
        section_types = {s.section_type for s in sections}
        
        # Default eligible sections are paragraph, tip, warning
        self.assertEqual(len(sections), 2)
        self.assertIn("paragraph", section_types)
        self.assertIn("tip", section_types)
        self.assertNotIn("heading", section_types)
        self.assertNotIn("code", section_types)

    @override_settings(IMAGE_ELIGIBLE_SECTION_TYPES=["tip"])
    def test_image_selector_with_overridden_settings(self):
        """
        Verify selector respects custom IMAGE_ELIGIBLE_SECTION_TYPES overrides.
        """
        selector = ImageSelector()
        sections = selector.select_sections_for_images(self.blog)
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0].section_type, "tip")

    def test_image_prompt_builder_includes_section_type(self):
        """
        Verify prompt builder generates context-aware prompt containing the section type.
        """
        builder = ImagePromptBuilder()
        prompt_obj = builder.build_prompt(
            blog_title=self.blog.title,
            blog_topic=self.blog.topic,
            section_heading="Test Heading",
            section_content="Test Content",
            section_type="warning"
        )
        self.assertIsInstance(prompt_obj, ImagePrompt)
        self.assertEqual(prompt_obj.section_type, "warning")
        self.assertIn("section type 'warning'", prompt_obj.prompt_text)
        self.assertIn("AI Image Automation", prompt_obj.prompt_text)
        self.assertIn("Test Content", prompt_obj.prompt_text)

    def test_image_validator_png_jpeg_headers(self):
        """
        Verify validation of image responses check bytes and raise ValueError on malformed data.
        """
        validator = ImageValidator()
        
        # PNG Check
        png_response = ImageResponse(b"\x89PNG\r\n\x1a\nimage-data", "dummy")
        # Should not raise
        validator.validate_image_data(png_response)
        
        # JPEG Check
        jpeg_response = ImageResponse(b"\xff\xd8image-data", "dummy")
        validator.validate_image_data(jpeg_response)

        # Empty data
        empty_response = ImageResponse(b"", "dummy")
        with self.assertRaises(ValueError) as ctx:
            validator.validate_image_data(empty_response)
        self.assertIn("No image bytes present", str(ctx.exception))

        # Unsupported format (e.g. text/html)
        html_response = ImageResponse(b"<html>text</html>", "dummy")
        with self.assertRaises(ValueError) as ctx:
            validator.validate_image_data(html_response)
        self.assertIn("Invalid image format", str(ctx.exception))

    @patch("services.image.storage.default_storage.save")
    def test_image_storage_saves_relative_to_media(self, mock_save):
        """
        Verify that ImageStorage calls default_storage save method with correct relative paths.
        """
        mock_save.return_value = "blog_images/test_image.png"
        storage = ImageStorage()
        res = ImageResponse(b"\x89PNG\r\n\x1a\n", "dummy")
        
        saved_path = storage.save_image("test_image.png", res)
        self.assertEqual(saved_path, "blog_images/test_image.png")
        mock_save.assert_called_once()

    @override_settings(IMAGE_ELIGIBLE_SECTION_TYPES=["paragraph", "tip"])
    @patch("services.image.storage.default_storage.save")
    def test_pipeline_successful_generation(self, mock_save):
        """
        Verify that a normal pipeline run executes correctly, saving
        images and registering BlogImage records for all eligible sections.
        """
        mock_save.side_effect = lambda f, c: f
        
        pipeline = ImagePipeline(provider_name="dummy")
        created_imgs = pipeline.generate_images_for_blog(self.blog)
        
        self.assertEqual(len(created_imgs), 2)
        self.assertEqual(BlogImage.objects.filter(blog=self.blog).count(), 2)
        
        # Assert relation to section is preserved
        img1 = created_imgs[0]
        self.assertEqual(img1.section, self.sec_paragraph)
        self.assertIn("section type 'paragraph'", img1.prompt)
        
        img2 = created_imgs[1]
        self.assertEqual(img2.section, self.sec_tip)
        self.assertIn("section type 'tip'", img2.prompt)

    @override_settings(IMAGE_ELIGIBLE_SECTION_TYPES=["paragraph", "tip"])
    @patch("services.image.storage.default_storage.save")
    @patch("services.image.dummy_provider.DummyImageProvider.generate_image")
    def test_pipeline_recovers_from_single_provider_failure(self, mock_generate, mock_save):
        """
        Verify that if provider fails (throws error) on one section, it compiles the other sections.
        """
        mock_save.side_effect = lambda f, c: f
        
        # Raise error on first section generate, succeed on second section generate
        success_response = ImageResponse(b"\x89PNG\r\n\x1a\n", "dummy")
        mock_generate.side_effect = [
            Exception("API Rate Limit Blocked."),
            success_response
        ]
        
        pipeline = ImagePipeline(provider_name="dummy")
        created_imgs = pipeline.generate_images_for_blog(self.blog)
        
        # One section failed, one succeeded.
        self.assertEqual(len(created_imgs), 1)
        self.assertEqual(BlogImage.objects.filter(blog=self.blog).count(), 1)
        self.assertEqual(created_imgs[0].section, self.sec_tip)

        # Blog status must remain unchanged
        self.assertEqual(self.blog.status, "generated")

    @override_settings(IMAGE_ELIGIBLE_SECTION_TYPES=["paragraph", "tip"])
    @patch("services.image.storage.ImageStorage.save_image")
    def test_pipeline_recovers_from_storage_failures(self, mock_storage_save):
        """
        Verify that if save_image fails on storage, it continues cleanly to next sections.
        """
        mock_storage_save.side_effect = [
            IOError("Disk Full"),
            "blog_images/success.png"
        ]
        
        pipeline = ImagePipeline(provider_name="dummy")
        created_imgs = pipeline.generate_images_for_blog(self.blog)
        
        self.assertEqual(len(created_imgs), 1)
        self.assertEqual(BlogImage.objects.filter(blog=self.blog).count(), 1)
        self.assertEqual(created_imgs[0].section, self.sec_tip)

    @override_settings(IMAGE_ELIGIBLE_SECTION_TYPES=[])
    def test_pipeline_no_eligible_sections(self):
        """
        Verify that if no section matches type criteria, it returns empty list cleanly.
        """
        pipeline = ImagePipeline(provider_name="dummy")
        created_imgs = pipeline.generate_images_for_blog(self.blog)
        self.assertEqual(len(created_imgs), 0)
        self.assertEqual(BlogImage.objects.filter(blog=self.blog).count(), 0)
