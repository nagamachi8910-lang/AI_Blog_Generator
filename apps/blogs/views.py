from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from apps.blogs.models import Blog
from services.render.renderer import render_section

@login_required
def blogs_list_view(request):
    blogs = Blog.objects.filter(author=request.user).order_by("-created_at")
    return render(request, "dashboard/blogs.html", {"blogs": blogs})

@login_required
def blog_detail_view(request, slug=None):
    blog = get_object_or_404(Blog, slug=slug, author=request.user)
    sections = blog.sections.all().order_by("order")
    
    rendered_sections = []
    toc = []
    
    for section in sections:
        html = render_section(section)
        rendered_sections.append(html)
        if section.heading:
            toc.append({
                "id": str(section.id),
                "title": section.heading
            })
            
    # Calculate reading time based on total word count (approx 200 words per minute)
    total_words = sum(len((s.content or "").split()) for s in sections)
    reading_time = max(1, round(total_words / 200))
    
    context = {
        "blog": blog,
        "rendered_sections": rendered_sections,
        "toc": toc,
        "reading_time": reading_time,
    }
    return render(request, "generator/blogreader.html", context)

@login_required
def favorites_view(request):
    return render(request, "emptypage/favroites_emptypage.html")

@login_required
def history_view(request):
    return render(request, "dashboard/history.html")

