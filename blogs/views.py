from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from blogs.repositories.blog_repository import BlogRepository
from ai_pipeline.models.blog_request import BlogRequest
from blogs.models import Blog
from .forms import BlogGenerationForm
from .services.blog_service import BlogService
from django.views.generic import TemplateView
from django.contrib import messages
from .forms import BlogEditForm
from .services.blog_update_service import BlogUpdateService
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
import json
from blogs.services.regenerate_service import RegenerateService
from .services.blog_regeneration_service import BlogRegenerationService

class GenerateBlogView(TemplateView):
    template_name = "blogs/generate_blog.html"


    def get(self, request):

        form = BlogGenerationForm()

        return self.render_to_response({
            "form": form,
        })

    def post(self, request):

        form = BlogGenerationForm(request.POST)

        if not form.is_valid():

            return self.render_to_response({
                "form": form,
            })

        data = form.cleaned_data

        request_model = BlogRequest(

            topic=data["topic"],

            content_brief=data["content_brief"],

            target_audience=data["target_audience"],

            tone=data["tone"],

            length=data["length"],

            keywords=[
                keyword.strip()
                for keyword in data["keywords"].split(",")
                if keyword.strip()
            ],
        )

        try:

            service = BlogService()

            blog = service.generate(

                request=request_model,

            )

            messages.success(
                request,
                "Blog generated successfully."
            )

            return redirect(
                "blogs:detail",
                blog.id,
            )

        except Exception as e:

            messages.error(
                request,
                str(e),
            )

            return self.render_to_response({
                "form": form,
            })
        
"""class PreviewBlogView(View):

    template_name = "blogs/preview_blog.html"

    def get(self, request, pk):

        blog = get_object_or_404(
            Blog.objects.prefetch_related("chapters"),
            pk=pk,
            is_deleted=False,
        )

        return render(
            request,
            self.template_name,
            {
                "blog": blog,
                "chapters": blog.chapters.all(),
            },
        )"""

class DashboardView(TemplateView):
    """
    User dashboard.
    """

    template_name = "blogs/dashboard.html"

    def get(self, request, *args, **kwargs):

        blogs = Blog.objects.filter(
            is_deleted=False,
        )

        total_blogs = blogs.count()

        draft_blogs = blogs.filter(
            status="draft"
        ).count()

        published_blogs = blogs.filter(
            status="published"
        ).count()

        recent_blogs = (
            blogs
            .order_by("-created_at")[:6]
        )

        total_images = 0

        for blog in recent_blogs:

            total_images += 2      # hero + conclusion

            total_images += (
                blog.chapters.count()
            )

        context = {

            "total_blogs": total_blogs,

            "draft_blogs": draft_blogs,

            "published_blogs": published_blogs,

            "recent_blogs": recent_blogs,

            "total_images": total_images,

            "storage_used": "Calculating...",

        }

        return self.render_to_response(context)
    


def blog_detail(request, blog_id):

    blog = BlogRepository.get_blog(blog_id)

    return render(

        request,

        "blogs/detail.html",

        {

            "blog": blog,

            "chapters": blog.chapters.all(),

        },

    )

def my_blogs(request):

    search = request.GET.get("q", "").strip()

    category = request.GET.get("category", "").strip()

    status = request.GET.get("status", "").strip()

    sort = request.GET.get("sort", "-created_at").strip()

    blogs = BlogRepository.get_user_blogs(

        search,

        category,

        status,

        sort,

    )

    paginator = Paginator(

        blogs,

        6,

    )

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    raw_categories = Blog.objects.filter(is_deleted=False).values_list("category", flat=True)
    categories = sorted(list(set(c.strip() for c in raw_categories if c and c.strip())))

    return render(

        request,

        "blogs/my_blogs.html",

        {

            "page_obj": page_obj,

            "search": search,

            "selected_category": category,

            "selected_status": status,

            "selected_sort": sort,

            "categories": categories,

        },

    )
def edit_blog(request, blog_id):

    blog = BlogRepository.get_blog(blog_id)

    return render(
        request,
        "blogs/edit_blog.html",
        {
            "blog": blog,
            "chapters": blog.chapters.all(),
        },
    )
@require_POST
def delete_blog(request, blog_id):

    try:

        blog = BlogRepository.get_blog(blog_id)

        BlogRepository.delete_blog(blog)

        return JsonResponse(
            {
                "success": True,
            }
        )

    except Blog.DoesNotExist:

        return JsonResponse(
            {
                "success": False,
                "message": "Blog not found."
            },
            status=404,
        )
@require_POST
def update_blog(request, blog_id):
    blog = BlogRepository.get_blog(blog_id)

    data = json.loads(request.body)

    BlogRepository.update_blog(

        blog,

        data,

    )

    return JsonResponse(

        {

            "success":True

        }

    )

@require_POST
def regenerate_paragraph(request):

    data = json.loads(request.body)

    paragraph = data["paragraph"]

    chapter_title = data.get("chapter_title", "")

    tone = data.get("tone", "Professional")

    audience = data.get("target_audience", "General")

    improved = RegenerateService.regenerate_paragraph(
        paragraph,
        chapter_title,
        tone,
        audience,
    )

    return JsonResponse(
        {
            "success": True,
            "paragraph": improved,
        }
    )

@require_POST
def regenerate_image(request):

    data = json.loads(request.body)

    stored = RegenerateService.regenerate_image(

        paragraphs=data["paragraphs"],

        generation_uuid=data["generation_uuid"],

        image_name=data["image_name"],

    )

    return JsonResponse({

        "success": True,

        "image": {

            "path": stored.public_url,

            "storage_path": stored.storage_path,

            "prompt": stored.prompt,

            "alt_text": stored.alt_text,

            "provider": stored.provider,

        }

    })

@require_POST
def regenerate_chapter(request):

    data = json.loads(request.body)

    chapter = RegenerateService.regenerate_chapter(

        title=data["title"],

        paragraphs=data["paragraphs"],

        bullet_points=data["bullet_points"],

        tone=data["tone"],

        audience=data["target_audience"],

    )

    return JsonResponse({

        "success":True,

        "chapter":chapter,

    })

@require_POST
def regenerate_entire_blog(request):

    data = json.loads(request.body)

    blog = BlogRepository.get_blog(
        data["blog_id"]
    )

    try:

        service = BlogRegenerationService()

        blog = service.regenerate(blog)

        return JsonResponse(
            {
                "success": True,
                "blog_id": blog.id,
            }
        )

    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "message": str(e),
            },
            status=500,
        )