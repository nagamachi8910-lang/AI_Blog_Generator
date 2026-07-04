from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.blogs.models import Blog, BlogSection, BlogImage

User = get_user_model()


class BlogModelTests(TestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="author1",
            email="author1@example.com",
            password="testpassword123"
        )

    def test_blog_creation(self):
        """
        Verify that Blog is created successfully and auto-slug is generated.
        """
        blog = Blog.objects.create(
            author=self.user,
            title="My First Test Blog Post",
            topic="Coding",
            tone="Informative",
            status="draft",
            summary="A short summary of our post",
            llm_provider="gemini",
            llm_model="gemini-1.5-pro"
        )
        self.assertEqual(blog.title, "My First Test Blog Post")
        self.assertEqual(blog.slug, "my-first-test-blog-post")
        self.assertEqual(str(blog), "My First Test Blog Post")
        self.assertIsNotNone(blog.id)

    def test_slug_uniqueness_collision(self):
        """
        Verify that duplicate titles generate unique slug suffixes.
        """
        blog1 = Blog.objects.create(author=self.user, title="Unique Topic")
        blog2 = Blog.objects.create(author=self.user, title="Unique Topic")
        blog3 = Blog.objects.create(author=self.user, title="Unique Topic")
        
        self.assertEqual(blog1.slug, "unique-topic")
        self.assertEqual(blog2.slug, "unique-topic-1")
        self.assertEqual(blog3.slug, "unique-topic-2")

    def test_blog_section_ordering(self):
        """
        Verify that BlogSection entries are retrieved in ascending order.
        """
        blog = Blog.objects.create(author=self.user, title="My Blog with Sections")
        sec2 = BlogSection.objects.create(
            blog=blog, 
            heading="Second Section", 
            content="This is section 2", 
            order=2, 
            section_type="paragraph"
        )
        sec1 = BlogSection.objects.create(
            blog=blog, 
            heading="First Section", 
            content="This is section 1", 
            order=1, 
            section_type="heading"
        )
        sec3 = BlogSection.objects.create(
            blog=blog, 
            heading="Third Section", 
            content="This is section 3", 
            order=3, 
            section_type="summary"
        )
        
        sections = list(blog.sections.all())
        self.assertEqual(len(sections), 3)
        self.assertEqual(sections[0].heading, "First Section")
        self.assertEqual(sections[1].heading, "Second Section")
        self.assertEqual(sections[2].heading, "Third Section")

    def test_estimated_reading_time(self):
        """
        Verify estimated reading time based on total section words.
        """
        blog = Blog.objects.create(author=self.user, title="My Reading Time Blog")
        
        # 0 words
        self.assertEqual(blog.estimated_reading_time(), 0)
        
        # Add 300 words
        sec_content = "word " * 300
        BlogSection.objects.create(blog=blog, content=sec_content, order=1)
        # 300 / 200 = 1.5, rounds to 2
        self.assertEqual(blog.estimated_reading_time(), 2)

        # Explicit overrides
        blog.reading_time = 5
        blog.save()
        self.assertEqual(blog.estimated_reading_time(), 5)

    def test_cascade_deletion(self):
        """
        Verify that deleting a Blog deletes sections and images.
        """
        blog = Blog.objects.create(author=self.user, title="Cascade Blog")
        section = BlogSection.objects.create(blog=blog, heading="Header", content="Desc", order=1)
        image = BlogImage.objects.create(
            blog=blog, 
            section=section, 
            prompt="A nice cover", 
            provider="stable-diffusion"
        )
        
        self.assertEqual(Blog.objects.count(), 1)
        self.assertEqual(BlogSection.objects.count(), 1)
        self.assertEqual(BlogImage.objects.count(), 1)
        
        # Delete blog
        blog.delete()
        
        self.assertEqual(Blog.objects.count(), 0)
        self.assertEqual(BlogSection.objects.count(), 0)
        self.assertEqual(BlogImage.objects.count(), 0)

    def test_section_delete_nullifies_image_section_link(self):
        """
        Verify that deleting a section does NOT delete the associated image, 
        but nullifies the section reference.
        """
        blog = Blog.objects.create(author=self.user, title="Nullify link Blog")
        section = BlogSection.objects.create(blog=blog, heading="Sec", order=1)
        image = BlogImage.objects.create(blog=blog, section=section, prompt="Details")
        
        self.assertEqual(BlogSection.objects.count(), 1)
        self.assertEqual(BlogImage.objects.count(), 1)
        
        # Delete section
        section.delete()
        
        self.assertEqual(BlogSection.objects.count(), 0)
        self.assertEqual(BlogImage.objects.count(), 1)
        
        image.refresh_from_db()
        self.assertIsNone(image.section)
