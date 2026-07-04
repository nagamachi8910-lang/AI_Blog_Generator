from django.contrib import admin
from .models import Blog, BlogSection, BlogImage


class BlogSectionInline(admin.TabularInline):
    model = BlogSection
    extra = 1
    ordering = ("order",)


class BlogImageInline(admin.TabularInline):
    model = BlogImage
    extra = 1
    fk_name = "blog"  # Explicitly specify fk_name because Blog has cover_image pointing to BlogImage, causing validation issues on auto-lookup.


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "status", "word_count", "reading_time", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "topic", "summary")
    inlines = [BlogSectionInline, BlogImageInline]


@admin.register(BlogSection)
class BlogSectionAdmin(admin.ModelAdmin):
    list_display = ("blog", "section_type", "heading", "order")
    list_filter = ("section_type", "blog")
    ordering = ("blog", "order")


@admin.register(BlogImage)
class BlogImageAdmin(admin.ModelAdmin):
    list_display = ("id", "blog", "is_cover", "provider", "model", "regeneration_count", "created_at")
    list_filter = ("is_cover", "provider", "created_at")
