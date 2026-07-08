from pydantic import BaseModel
from django.db import transaction
from django.db.models import Q

from blogs.models import Blog
from blogs.repositories.chapter_repository import ChapterRepository


def serialize(value):
    """
    Recursively convert Pydantic models into
    plain Python objects that Django JSONField
    can store.
    """

    if value is None:
        return None

    if isinstance(value, BaseModel):
        return value.model_dump()

    if isinstance(value, list):
        return [serialize(item) for item in value]

    if isinstance(value, dict):
        return {
            key: serialize(val)
            for key, val in value.items()
        }

    return value


class BlogRepository:

    @staticmethod
    @transaction.atomic
    def create_blog(
        blog,
        generation_uuid,
    ):
        """
        Save a generated blog and all its chapters.
        """

        db_blog = Blog.objects.create(

            # ------------------------------------
            # Blog Info
            # ------------------------------------

            generation_uuid=generation_uuid,
            topic=blog.blog_info.topic,
            language=blog.blog_info.language,
            tone=blog.blog_info.tone,
            blog_type=blog.blog_info.blog_type,
            target_audience=blog.blog_info.target_audience,

            # ------------------------------------
            # Metadata
            # ------------------------------------

            title=blog.metadata.title,
            slug=blog.metadata.slug,
            description=blog.metadata.description,
            category=blog.metadata.category,
            keywords=serialize(blog.metadata.keywords),
            tags=serialize(blog.metadata.tags),

            # ------------------------------------
            # Rich Content
            # ------------------------------------

            hero=serialize(blog.hero),

            key_takeaways=serialize(
                blog.key_takeaways
            ),

            faq=serialize(
                blog.faq
            ),

            resources=serialize(
                blog.resources
            ),

            call_to_action=serialize(
                blog.call_to_action
            ),

            conclusion=serialize(
                blog.conclusion
            ),

            # ------------------------------------
            # Generation
            # ------------------------------------

            processing_status="completed",

            status="draft",

            llm_provider="gemini",

            image_provider="pollinations",

        )

        ChapterRepository.bulk_create(
            db_blog,
            blog.chapters,
        )

        return db_blog

    @staticmethod
    @transaction.atomic
    def replace_blog(
        existing_blog,
        generated_blog,
    ):
        """
        Replace an existing blog with newly generated content.
        Keeps the same Blog ID and metadata.
        """

        # ------------------------------------
        # Blog Information
        # ------------------------------------
        existing_blog.topic = generated_blog.blog_info.topic
        existing_blog.language = generated_blog.blog_info.language
        existing_blog.tone = generated_blog.blog_info.tone
        existing_blog.blog_type = generated_blog.blog_info.blog_type
        existing_blog.target_audience = generated_blog.blog_info.target_audience

        # ------------------------------------
        # Metadata
        # ------------------------------------

        existing_blog.title = generated_blog.metadata.title
        existing_blog.slug = generated_blog.metadata.slug
        existing_blog.description = generated_blog.metadata.description
        existing_blog.category = generated_blog.metadata.category

        existing_blog.keywords = serialize(
            generated_blog.metadata.keywords
        )

        existing_blog.tags = serialize(
            generated_blog.metadata.tags
        )

        # ------------------------------------
        # Rich Content
        # ------------------------------------

        existing_blog.hero = serialize(
            generated_blog.hero
        )

        existing_blog.key_takeaways = serialize(
            generated_blog.key_takeaways
        )

        existing_blog.faq = serialize(
            generated_blog.faq
        )

        existing_blog.resources = serialize(
            generated_blog.resources
        )

        existing_blog.call_to_action = serialize(
            generated_blog.call_to_action
        )

        existing_blog.conclusion = serialize(
            generated_blog.conclusion
        )

        existing_blog.processing_status = "completed"

        existing_blog.save()

        # ------------------------------------
        # Replace Chapters
        # ------------------------------------

        existing_blog.chapters.all().delete()

        ChapterRepository.bulk_create(
            existing_blog,
            generated_blog.chapters,
        )

        return existing_blog
    @staticmethod
    def get_blog(blog_id):

        return Blog.objects.prefetch_related(
            "chapters"
        ).get(
            id=blog_id,
            is_deleted=False,
        )

    
    @staticmethod
    def get_user_blogs(
        search="",
        category="",
        status="",
        sort="-created_at",
    ):

        blogs = Blog.objects.filter(
            is_deleted=False,
        )

        if search:

            blogs = blogs.filter(

                Q(title__icontains=search) |

                Q(topic__icontains=search) |

                Q(description__icontains=search)

            )

        if category:

            blogs = blogs.filter(
                category=category
            )

        if status:

            blogs = blogs.filter(
                status=status
            )

        return blogs.order_by(sort)

    @staticmethod
    @transaction.atomic
    def update_blog(blog, data):

        # -----------------------------
        # Metadata
        # -----------------------------

        blog.title = data["title"]

        blog.description = data["description"]

        blog.category = data["category"]

        blog.language = data["language"]

        blog.tone = data["tone"]

        blog.target_audience = data["target_audience"]

        blog.status = data["status"]
        if "hero" in data:

            blog.hero = data["hero"]
        blog.save()

        # -----------------------------
        # Chapters
        # -----------------------------

        for chapter_data in data["chapters"]:

            chapter = blog.chapters.get(

                id=chapter_data["id"]

            )

            chapter.title = chapter_data["title"]

            chapter.paragraphs = chapter_data["paragraphs"]

            chapter.bullet_points = chapter_data["bullet_points"]

            if "image" in chapter_data:

                chapter.image = chapter_data["image"]

            chapter.save()

        return blog

    @staticmethod
    def delete_blog(blog):

        blog.is_deleted = True

        blog.save(
            update_fields=["is_deleted"]
        )

    @staticmethod
    def save(blog):

        blog.save()

        return blog