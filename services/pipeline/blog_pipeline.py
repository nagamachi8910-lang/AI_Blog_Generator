import logging
from django.db import transaction
from django.utils.text import slugify
from apps.blogs.models import Blog, BlogSection
from services.ai.prompt_builder import PromptBuilder, Prompt
from services.ai.provider import get_provider
from services.ai.parser import parse_blog_response, ParsedBlog

logger = logging.getLogger(__name__)


class BlogPipeline:
    def generate(
        self,
        author,
        topic: str,
        tone: str,
        title: str = None,
        llm_provider: str = "dummy",
        llm_model: str = "default"
    ) -> Blog:
        """
        Public orchestrator method to execute the blog generation pipeline.
        """
        self._validate_request(topic, tone)
        
        # 1. Create Blog in database with initial status
        blog = self._create_blog(author, topic, tone, title, llm_provider, llm_model)
        
        try:
            # 2. Transition status to generating
            self._update_status(blog, "generating")
            
            # 3. Build structured prompt
            prompt = self._build_prompt(topic, tone, title)
            
            # 4. Invoke LLM provider
            raw_text = self._call_ai(prompt, llm_provider, llm_model)
            
            # 5. Parse response content
            parsed_blog = self._parse_response(raw_text)
            
            # 6. Persist sections and metadata in database atomically
            self._persist_blog_data(blog, parsed_blog)
            
            # 7. Transition status to completed
            self._complete_generation(blog)
            
            # 8. Trigger image generation as an independent service
            try:
                from services.image.pipeline import ImagePipeline
                image_pipeline = ImagePipeline()
                image_pipeline.generate_images_for_blog(blog)
            except Exception as img_err:
                logger.error(f"Failed to run image generation pipeline: {img_err}")
            
        except Exception as e:
            logger.error(f"AI Generation Pipeline error: {e}")
            self._mark_as_failed(blog)
            raise
            
        return blog

    def _validate_request(self, topic: str, tone: str):
        if not topic or not topic.strip():
            raise ValueError("Topic is required.")
        if not tone or not tone.strip():
            raise ValueError("Tone is required.")

    def _create_blog(
        self,
        author,
        topic: str,
        tone: str,
        title: str,
        llm_provider: str,
        llm_model: str
    ) -> Blog:
        blog_title = title or f"AI Blog: {topic}"
        return Blog.objects.create(
            author=author,
            title=blog_title,
            topic=topic,
            tone=tone,
            status="queued",
            llm_provider=llm_provider,
            llm_model=llm_model
        )

    def _update_status(self, blog: Blog, status: str):
        blog.status = status
        blog.save(update_fields=["status"])

    def _build_prompt(self, topic: str, tone: str, title: str) -> Prompt:
        return PromptBuilder.build_blog_prompt(topic, tone, title)

    def _call_ai(self, prompt: Prompt, provider_name: str, model: str) -> str:
        provider = get_provider(provider_name)
        return provider.generate_content(prompt, model)

    def _parse_response(self, raw_text: str) -> ParsedBlog:
        return parse_blog_response(raw_text)

    def _persist_blog_data(self, blog: Blog, parsed_blog: ParsedBlog):
        with transaction.atomic():
            blog.title = parsed_blog.title or blog.title
            
            # Refresh slug dynamically as the title may be refined by AI
            if parsed_blog.title:
                base_slug = slugify(parsed_blog.title) or "untitled"
                slug = base_slug
                count = 1
                while Blog.objects.filter(slug=slug).exclude(pk=blog.pk).exists():
                    slug = f"{base_slug}-{count}"
                    count += 1
                blog.slug = slug
                
            blog.summary = parsed_blog.summary
            blog.save()
            
            # Clean existing sections to prevent duplication/orphans on retries
            blog.sections.all().delete()
            
            # Save sections
            total_words = 0
            for sec in parsed_blog.sections:
                BlogSection.objects.create(
                    blog=blog,
                    section_type=sec.section_type,
                    heading=sec.heading,
                    content=sec.content,
                    order=sec.order,
                    metadata=sec.metadata,
                    generation_metadata=sec.generation_metadata
                )
                if sec.content:
                    total_words += len(sec.content.split())
                    
            blog.word_count = total_words
            blog.save(update_fields=["title", "slug", "summary", "word_count"])

    def _complete_generation(self, blog: Blog):
        blog.reading_time = blog.estimated_reading_time()
        blog.status = "generated"
        blog.save(update_fields=["reading_time", "status"])

    def _mark_as_failed(self, blog: Blog):
        try:
            blog.status = "failed"
            blog.save(update_fields=["status"])
        except Exception as e:
            logger.critical(f"Status transition to failed crashed: {e}")
