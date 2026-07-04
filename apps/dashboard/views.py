from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.blogs.models import Blog, BlogImage

def landing_page_view(request):
    return render(request, "landing/landingpage.html")

@login_required
def dashboard_view(request):
    blogs = Blog.objects.filter(author=request.user)
    
    total_blogs = blogs.count()
    published_blogs = blogs.filter(status="published").count()
    draft_blogs = blogs.filter(status="draft").count()
    failed_blogs = blogs.filter(status="failed").count()
    
    total_images = BlogImage.objects.filter(blog__author=request.user).count()
    recent_blogs = blogs.order_by("-created_at")[:5]
    
    context = {
        "total_blogs": total_blogs,
        "published_blogs": published_blogs,
        "draft_blogs": draft_blogs,
        "failed_blogs": failed_blogs,
        "total_images": total_images,
        "recent_blogs": recent_blogs,
    }
    return render(request, "dashboard/dashboard.html", context)

@login_required
def profile_view(request):
    return render(request, "dashboard/profile.html")

@login_required
def settings_view(request):
    return render(request, "dashboard/settings.html")

