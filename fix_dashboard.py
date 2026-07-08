import os

target = 'dashboard/views.py'

logic = '''from django.conf import settings
from django.shortcuts import render
from blogs.models import Blog

def dashboard_view(request):
    blogs = Blog.objects.filter(is_deleted=False).prefetch_related('chapters')
    
    blogs_created = blogs.count()
    draft_blogs = sum(1 for b in blogs if b.status == 'draft')
    published_blogs = sum(1 for b in blogs if b.status == 'published')
    
    images_generated = 0
    for blog in blogs:
        if blog.hero and isinstance(blog.hero, dict) and blog.hero.get("image", {}).get("path"):
            images_generated += 1
        if blog.conclusion and isinstance(blog.conclusion, dict) and blog.conclusion.get("image", {}).get("path"):
            images_generated += 1
        for chapter in blog.chapters.all():
            if chapter.image and isinstance(chapter.image, dict) and chapter.image.get("path"):
                images_generated += 1

    context = {
        "blogs_created": blogs_created,
        "draft_blogs": draft_blogs,
        "published_blogs": published_blogs,
        "images_generated": images_generated,
        "SUPABASE_URL": settings.SUPABASE_URL,
        "SUPABASE_ANON_KEY": settings.SUPABASE_ANON_KEY,
    }
    return render(
        request,
        "blogs/dashboard.html",
        context
    )
'''

with open(target, 'w', encoding='utf-8') as f:
    f.write(logic)

print("Dashboard views fixed")
