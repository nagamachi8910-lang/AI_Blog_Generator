from services.pipeline.blog_pipeline import BlogPipeline
from apps.blogs.models import Blog

class GenerationService:
    @staticmethod
    def generate_blog(user, topic: str, tone: str, provider: str, model: str) -> Blog:
        """
        Orchestrates the blog generation pipeline via BlogPipeline, keeping views thin.
        """
        pipeline = BlogPipeline()
        return pipeline.generate(
            author=user,
            topic=topic,
            tone=tone,
            llm_provider=provider,
            llm_model=model
        )
