from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.blogs.models import Blog, BlogSection, BlogImage
from unittest.mock import patch

User = get_user_model()


class BlogGenerationIntegrationTests(TestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.user = User.objects.create_user(
            username="testcoder",
            email="coder@example.com",
            password="testpassword",
            supabase_user_id="sb-test-coder-999"
        )
        self.other_user = User.objects.create_user(
            username="othercoder",
            email="other@example.com",
            password="testpassword",
            supabase_user_id="sb-other-999"
        )

    def test_unauthorized_generator_access_redirects(self):
        """
        Verify that unauthorized access to the generator, process, detail views,
        and dashboard redirects to login.
        """
        generator_url = reverse("generator:generator")
        process_url = reverse("generator:process")
        api_url = reverse("generator:api_generate")
        dashboard_url = reverse("dashboard:dashboard")
        
        for url in [generator_url, process_url, dashboard_url]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn("/accounts/login/?next=", response.url)

        # API post redirect check
        api_response = self.client.post(api_url)
        self.assertEqual(api_response.status_code, 302)

    def test_generator_form_submission_stores_session(self):
        """
        Verify that submitting the generation form stores configurations in session
        and redirects to the processing page.
        """
        self.client.force_login(self.user)
        
        post_data = {
            "topic": "Integrating Django pipelines with Supabase",
            "tone": "professional",
            "provider": "gemini",
            "model": "gemini-1.5-flash",
        }
        
        response = self.client.post(reverse("generator:generator"), post_data)
        self.assertRedirects(response, reverse("generator:process"))
        
        # Verify session values
        session = self.client.session
        self.assertEqual(session["generation_params"]["topic"], post_data["topic"])
        self.assertEqual(session["generation_params"]["tone"], post_data["tone"])
        self.assertEqual(session["generation_params"]["provider"], post_data["provider"])
        self.assertEqual(session["generation_params"]["model"], post_data["model"])

    def test_process_view_verifies_session_data(self):
        """
        Verify that the processing page loads successfully if session settings are present,
        and redirects back to the generator if parameters are missing.
        """
        self.client.force_login(self.user)
        
        # Access process page without session parameters
        response_no_session = self.client.get(reverse("generator:process"))
        self.assertRedirects(response_no_session, reverse("generator:generator"))
        
        # Access process page with settings
        session = self.client.session
        session["generation_params"] = {
            "topic": "Superb Integration Testing",
            "tone": "inspiring",
            "provider": "dummy",
            "model": "dummy-model",
        }
        session.save()
        
        response_with_session = self.client.get(reverse("generator:process"))
        self.assertEqual(response_with_session.status_code, 200)
        self.assertContains(response_with_session, "Superb Integration Testing")

    @patch("services.generation_service.GenerationService.generate_blog")
    def test_api_generate_success(self, mock_generate):
        """
        Verify that POSTing to generator API runs the generation service,
        creates the blog successfully, and returns a JSON success response.
        """
        self.client.force_login(self.user)
        
        # Mocking generation service response to return a mock Blog model
        mock_blog = Blog.objects.create(
            author=self.user,
            title="Generated Test Blog",
            slug="generated-test-blog",
            status="published",
            topic="Testing",
            tone="professional"
        )
        mock_generate.return_value = mock_blog
        
        session = self.client.session
        session["generation_params"] = {
            "topic": "Testing Django Services",
            "tone": "professional",
            "provider": "dummy",
            "model": "dummy-model",
        }
        session.save()
        
        response = self.client.post(reverse("generator:api_generate"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "status": "success",
            "redirect_url": reverse("blogs:detail", kwargs={"slug": mock_blog.slug})
        })

    @patch("services.generation_service.GenerationService.generate_blog")
    def test_api_generate_failure(self, mock_generate):
        """
        Verify that if generation service fails, it returns a 500 error JSON message.
        """
        self.client.force_login(self.user)
        mock_generate.side_effect = Exception("AI generation limit exceeded")
        
        session = self.client.session
        session["generation_params"] = {
            "topic": "Failing Gracefully",
            "tone": "formal",
            "provider": "dummy",
            "model": "dummy-model",
        }
        session.save()
        
        response = self.client.post(reverse("generator:api_generate"))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {
            "status": "error",
            "message": "AI generation limit exceeded"
        })

    def test_blog_detail_view_permissions_and_rendering(self):
        """
        Verify that:
        1. Users cannot access other users' blogs (returns 404).
        2. Users can view their own blogs which parses and renders sections to HTML.
        3. Table of contents lists headings with sec-<section-id> ids.
        """
        blog = Blog.objects.create(
            author=self.user,
            title="Secure Integration Testing",
            slug="secure-integration-testing",
            status="published",
            topic="Security"
        )
        section = BlogSection.objects.create(
            blog=blog,
            section_type="heading",
            heading="Section One Heading",
            content="This is the heading content",
            order=1
        )
        
        # Test other user accessing -> 404
        self.client.force_login(self.other_user)
        response_unauthorized = self.client.get(reverse("blogs:detail", kwargs={"slug": blog.slug}))
        self.assertEqual(response_unauthorized.status_code, 404)
        
        # Test owner accessing -> 200, checks dynamic rendering
        self.client.force_login(self.user)
        response_authorized = self.client.get(reverse("blogs:detail", kwargs={"slug": blog.slug}))
        self.assertEqual(response_authorized.status_code, 200)
        
        # Check rendered heading incorporates dynamic id
        self.assertContains(response_authorized, f'id="sec-{section.id}"')
        self.assertContains(response_authorized, "Section One Heading")
        
        # Check table of contents includes heading links
        self.assertContains(response_authorized, f'href="#sec-{section.id}"')

    def test_dashboard_metrics_display(self):
        """
        Verify that the dashboard displays the total blog counts and recent list
        of blogs generated specifically by the user.
        """
        # Create user blogs
        b1 = Blog.objects.create(author=self.user, title="B1", slug="b1", status="published")
        b2 = Blog.objects.create(author=self.user, title="B2", slug="b2", status="draft")
        b3 = Blog.objects.create(author=self.user, title="B3", slug="b3", status="failed")
        
        # Create user images
        BlogImage.objects.create(blog=b1, is_cover=True)
        BlogImage.objects.create(blog=b2, is_cover=False)
        
        # Create other user blog -> shouldn't count
        Blog.objects.create(author=self.other_user, title="Other", slug="oth", status="published")
        
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard:dashboard"))
        self.assertEqual(response.status_code, 200)
        
        # Verify context values passed to template
        self.assertEqual(response.context["total_blogs"], 3)
        self.assertEqual(response.context["published_blogs"], 1)
        self.assertEqual(response.context["draft_blogs"], 1)
        self.assertEqual(response.context["failed_blogs"], 1)
        self.assertEqual(response.context["total_images"], 2)
        
        # Verify recent blogs list displays client side
        self.assertContains(response, "B1")
        self.assertContains(response, "B2")
        self.assertContains(response, "B3")
        self.assertNotContains(response, "Other")
