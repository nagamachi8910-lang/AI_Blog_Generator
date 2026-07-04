import uuid
from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils.text import slugify


class Blog(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("queued", "Queued"),
        ("generating", "Generating"),
        ("generated", "Generated"),
        ("editing", "Editing"),
        ("published", "Published"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blogs"
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    topic = models.CharField(max_length=255, blank=True)
    tone = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    summary = models.TextField(blank=True)
    word_count = models.PositiveIntegerField(default=0)
    reading_time = models.PositiveIntegerField(default=0)
    
    # ForeignKey to associated cover image (BlogImage)
    cover_image = models.ForeignKey(
        "BlogImage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+"
    )
    
    llm_provider = models.CharField(max_length=50, blank=True)
    llm_model = models.CharField(max_length=50, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or "untitled"
            slug = base_slug
            count = 1
            while Blog.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{count}"
                count += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def estimated_reading_time(self) -> int:
        """
        Calculates value based on actual sections word count.
        Falls back to stored reading_time if positive.
        """
        if self.reading_time > 0:
            return self.reading_time
            
        words = sum(len(sec.content.split()) for sec in self.sections.all())
        if words == 0:
            return 0
        return max(1, round(words / 200))

    def get_absolute_url(self) -> str:
        return reverse("blogs:detail", kwargs={"slug": self.slug})

    def __str__(self):
        return self.title


class BlogSection(models.Model):
    SECTION_CHOICES = [
        ("heading", "Heading"),
        ("paragraph", "Paragraph"),
        ("image", "Image"),
        ("code", "Code"),
        ("table", "Table"),
        ("quote", "Quote"),
        ("tip", "Tip"),
        ("warning", "Warning"),
        ("faq", "FAQ"),
        ("summary", "Summary"),
    ]

    blog = models.ForeignKey(
        Blog,
        on_delete=models.CASCADE,
        related_name="sections"
    )
    section_type = models.CharField(
        max_length=50,
        choices=SECTION_CHOICES,
        default="paragraph"
    )
    heading = models.CharField(max_length=255, blank=True)
    content = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    generation_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        type_display = self.get_section_type_display()
        title_segment = self.heading or (self.content[:30] + "...") if self.content else "Empty"
        return f"Section {self.order} ({type_display}) - {title_segment}"


class BlogImage(models.Model):
    blog = models.ForeignKey(
        Blog,
        on_delete=models.CASCADE,
        related_name="images"
    )
    # Optional FK to link an image to a specific blog section
    section = models.ForeignKey(
        BlogSection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="section_images"
    )
    image = models.ImageField(upload_to="blog_images/", blank=True, null=True)
    prompt = models.TextField(blank=True)
    provider = models.CharField(max_length=50, blank=True)
    model = models.CharField(max_length=50, blank=True)
    is_cover = models.BooleanField(default=False)
    regeneration_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Image {self.id} for Blog: {self.blog.title[:30]}"
