from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.blogs.models import Blog, BlogSection, BlogImage
from services.render.renderer import render_section, RenderDescriptor, get_renderer_for_type
from services.render.table_parser import parse_markdown_table

User = get_user_model()


class BlogRendererTests(TestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="renderer_user",
            email="renderer@example.com",
            password="pwd123456user"
        )
        self.blog = Blog.objects.create(
            author=self.user,
            title="Blog rendering demo",
            topic="Engines",
            status="generated"
        )

    def test_renderer_heading_and_paragraph(self):
        """
        Verify heading and paragraph sections produce accurate render descriptors and HTML.
        """
        sec_h = BlogSection.objects.create(
            blog=self.blog,
            section_type="heading",
            heading="Welcome Main Heading",
            content="Subtitle description string",
            order=1
        )
        sec_p = BlogSection.objects.create(
            blog=self.blog,
            section_type="paragraph",
            content="Regular paragraph content.",
            order=2
        )
        
        # Heading Section
        html_h = render_section(sec_h)
        self.assertIn("Welcome Main Heading", html_h)
        self.assertIn("Subtitle description string", html_h)
        self.assertIn("blog-section-heading", html_h)

        # Paragraph Section
        html_p = render_section(sec_p)
        self.assertIn("Regular paragraph content.", html_p)
        self.assertIn("blog-section-paragraph", html_p)

    def test_renderer_code_blocks_with_and_without_metadata(self):
        """
        Verify syntax highlighting resolves language settings from section metadata correctly.
        """
        # Code block WITH metadata
        sec_code_meta = BlogSection.objects.create(
            blog=self.blog,
            section_type="code",
            heading="Python script",
            content="def run():\n    print('Hello')",
            metadata={"language": "python"}
        )
        html_meta = render_section(sec_code_meta)
        self.assertIn("Python script", html_meta)
        self.assertIn("data-language=\"python\"", html_meta)
        self.assertIn("def run():", html_meta)
        self.assertIn("print", html_meta)

        # Code block WITHOUT metadata (empty metadata)
        sec_code_empty = BlogSection.objects.create(
            blog=self.blog,
            section_type="code",
            content="console.log('empty');",
            metadata={}
        )
        html_empty = render_section(sec_code_empty)
        self.assertIn("data-language=\"text\"", html_empty)
        self.assertIn("console.log", html_empty)

    def test_renderer_large_tables_parsing(self):
        """
        Verify large markdown tables parse cleanly and map correctly to styled HTML lines.
        """
        markdown_table = (
            "| Column 1 | Column 2 | Column 3 |\n"
            "|:---|---|:---:|\n"
            "| Row A1 | Row A2 | Row A3 |\n"
            "| Row B1 | Row B2 | Row B3 |\n"
        )
        
        # Test table parser module directly
        headers, rows = parse_markdown_table(markdown_table)
        self.assertEqual(headers, ["Column 1", "Column 2", "Column 3"])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], ["Row A1", "Row A2", "Row A3"])
        self.assertEqual(rows[1], ["Row B1", "Row B2", "Row B3"])

        # Test Renderer
        sec_table = BlogSection.objects.create(
            blog=self.blog,
            section_type="table",
            heading="Grid Comparison",
            content=markdown_table
        )
        html_table = render_section(sec_table)
        self.assertIn("Grid Comparison", html_table)
        self.assertIn("Column 1", html_table)
        self.assertIn("Row B3", html_table)
        self.assertIn("blog-section-table", html_table)

    def test_renderer_quotes_tips_and_warnings(self):
        """
        Verify CSS structures and metadata bindings load correctly for advice elements.
        """
        sec_quote = BlogSection.objects.create(
            blog=self.blog,
            section_type="quote",
            heading="Albert Einstein",
            content="Imagination is more important than knowledge."
        )
        sec_tip = BlogSection.objects.create(
            blog=self.blog,
            section_type="tip",
            heading="Pro Tip",
            content="Perform regular database compaction steps."
        )
        sec_warn = BlogSection.objects.create(
            blog=self.blog,
            section_type="warning",
            heading="Heads Up",
            content="Deprecation warning for legacy API keys."
        )

        self.assertIn("Albert Einstein", render_section(sec_quote))
        self.assertIn("blog-section-tip", render_section(sec_tip))
        self.assertIn("Deprecation warning", render_section(sec_warn))

    def test_renderer_faq_normalization(self):
        """
        Verify FAQ normalization checks parse question and answer fragments correctly.
        """
        # Valid FAQ Q&A format
        valid_faq = (
            "Q: What is Django?\n"
            "A: Django is a Python-based web framework.\n"
            "Q: Why use Python?\n"
            "A: Python is readable and powerful.\n"
        )
        sec_faq_valid = BlogSection.objects.create(
            blog=self.blog,
            section_type="faq",
            content=valid_faq
        )
        html_faq = render_section(sec_faq_valid)
        self.assertIn("Q: What is Django?", html_faq)
        self.assertIn("A: Django is a Python-based web framework.", html_faq)

        # Invalid/Malformed/No-Marker FAQ format (should fall back safely)
        invalid_faq = "Just normal sentence content without Q & A formatting."
        sec_faq_invalid = BlogSection.objects.create(
            blog=self.blog,
            section_type="faq",
            heading="Faq Fallback Heading",
            content=invalid_faq
        )
        html_invalid = render_section(sec_faq_invalid)
        self.assertIn("Q: Faq Fallback Heading", html_invalid)
        self.assertIn("A: Just normal sentence content", html_invalid)

    def test_renderer_automatically_resolves_blog_images(self):
        """
        Verify that associated BlogImage records are query resolved and render.
        """
        sec_p = BlogSection.objects.create(
            blog=self.blog,
            section_type="paragraph",
            content="Image section example text."
        )
        
        # Case 1: Missing/No images
        html_no_img = render_section(sec_p)
        self.assertNotIn("blog-image-wrapper", html_no_img)

        # Case 2: Assorted images
        img = BlogImage.objects.create(
            blog=self.blog,
            section=sec_p,
            image="blog_images/diagram.png",
            prompt="A diagram of MVC pattern"
        )
        
        html_with_img = render_section(sec_p)
        self.assertIn("blog-image-wrapper", html_with_img)
        self.assertIn("diagram.png", html_with_img)
        self.assertIn("A diagram of MVC pattern", html_with_img)

    def test_renderer_unsupported_section_type_raises_value_error(self):
        """
        Verify that unsupported section types reject generation with a ValueError.
        """
        sec_unsupported = BlogSection.objects.create(
            blog=self.blog,
            section_type="unknown_category_type",
            content="Content"
        )
        with self.assertRaises(ValueError) as ctx:
            render_section(sec_unsupported)
        self.assertIn("Unsupported section type: 'unknown_category_type'", str(ctx.exception))
