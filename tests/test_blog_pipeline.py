from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from apps.blogs.models import Blog
from services.pipeline.blog_pipeline import BlogPipeline

User = get_user_model()


class BlogPipelineTests(TestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="pipeline_author",
            email="author@example.com",
            password="securepassword123"
        )
        self.pipeline = BlogPipeline()

    def test_successful_blog_generation(self):
        """
        Verify that a complete successful generation runs the pipeline steps,
        saving sections, computing word count, reading time, and updating status to generated.
        """
        blog = self.pipeline.generate(
            author=self.user,
            topic="Clean Code",
            tone="Professional",
            title="Clean Code Guidelines",
            llm_provider="dummy"
        )
        
        self.assertEqual(blog.status, "generated")
        self.assertEqual(blog.topic, "Clean Code")
        self.assertEqual(blog.tone, "Professional")
        self.assertEqual(blog.title, "Mock Title: AI Design and Architecture")
        
        # Word count and reading time should be computed
        self.assertGreater(blog.word_count, 0)
        self.assertGreater(blog.reading_time, 0)
        
        # Sections check
        sections = list(blog.sections.all())
        self.assertEqual(len(sections), 3)
        self.assertEqual(sections[0].section_type, "heading")
        self.assertEqual(sections[1].section_type, "paragraph")
        self.assertEqual(sections[2].section_type, "summary")

    def test_input_validation_empty_topic(self):
        """
        Verify that an empty or missing topic raises a ValueError and creates no Blog.
        """
        with self.assertRaises(ValueError) as ctx:
            self.pipeline.generate(author=self.user, topic="", tone="Informative")
        self.assertIn("topic", str(ctx.exception).lower())
        
        self.assertEqual(Blog.objects.count(), 0)

    def test_input_validation_empty_tone(self):
        """
        Verify that an empty or missing tone raises a ValueError.
        """
        with self.assertRaises(ValueError) as ctx:
            self.pipeline.generate(author=self.user, topic="AI Technology", tone="  ")
        self.assertIn("tone", str(ctx.exception).lower())
        
        self.assertEqual(Blog.objects.count(), 0)

    @patch("services.pipeline.blog_pipeline.get_provider")
    def test_ai_provider_failure_marks_failed(self, mock_get_provider):
        """
        Verify that if the AI provider raises an exception, the blog status
        transitions to 'failed' and no sections are persisted.
        """
        mock_provider = MagicMock()
        mock_provider.generate_content.side_effect = Exception("API quota exceeded.")
        mock_get_provider.return_value = mock_provider
        
        with self.assertRaises(Exception) as ctx:
            self.pipeline.generate(
                author=self.user,
                topic="Failing Blog",
                tone="Humerous",
                llm_provider="failing-provider"
            )
        self.assertIn("API quota exceeded", str(ctx.exception))
        
        # Verify blog exists and transitioned to failed
        self.assertEqual(Blog.objects.count(), 1)
        blog = Blog.objects.first()
        self.assertEqual(blog.status, "failed")
        self.assertEqual(blog.sections.count(), 0)

    @patch("services.pipeline.blog_pipeline.parse_blog_response")
    def test_parsing_failure_marks_failed_and_rolls_back_atomic_transaction(self, mock_parse):
        """
        Verify that if parsing fails (raises value error), the Blog status transitions to 'failed',
        and no partial updates or sections are saved in the database.
        """
        mock_parse.side_effect = ValueError("Malformed schema: missing TITLE divider.")
        
        with self.assertRaises(ValueError) as ctx:
            self.pipeline.generate(
                author=self.user,
                topic="Malformed Output",
                tone="Corporate"
            )
        self.assertIn("malformed", str(ctx.exception).lower())
        
        self.assertEqual(Blog.objects.count(), 1)
        blog = Blog.objects.first()
        self.assertEqual(blog.status, "failed")
        
        # Word count and reading time should remain 0
        self.assertEqual(blog.word_count, 0)
        self.assertEqual(blog.reading_time, 0)
        # Sections should remain empty
        self.assertEqual(blog.sections.count(), 0)
