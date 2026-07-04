from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from services.generation_service import GenerationService


@login_required
def generator_view(request):
    if request.method == "POST":
        topic = request.POST.get("topic", "").strip()
        tone = request.POST.get("tone", "").strip()
        provider = request.POST.get("provider", "dummy").strip()
        model = request.POST.get("model", "default").strip()

        if not topic or not tone:
            context = {
                "error": "Topic and Tone are required.",
                "topic": topic,
                "tone": tone,
            }
            return render(request, "generator/bloggenerator.html", context)

        request.session["generation_params"] = {
            "topic": topic,
            "tone": tone,
            "provider": provider,
            "model": model,
        }
        return redirect("generator:process")

    return render(request, "generator/bloggenerator.html")


@login_required
def process_view(request):
    params = request.session.get("generation_params")
    if not params:
        return redirect("generator:generator")
    return render(request, "generator/process.html", {"params": params})


@login_required
@require_POST
def api_generate_view(request):
    """
    Standardized API to trigger blog generation and return success or failure responses.
    """
    params = request.session.get("generation_params")
    if not params:
        return JsonResponse({
            "status": "error",
            "message": "No active generation parameters found in session."
        }, status=400)

    # Pop session parameters so retry/reload doesn't re-trigger generation automatically
    request.session.pop("generation_params", None)

    topic = params.get("topic")
    tone = params.get("tone")
    provider = params.get("provider")
    model = params.get("model")

    try:
        blog = GenerationService.generate_blog(
            user=request.user,
            topic=topic,
            tone=tone,
            provider=provider,
            model=model
        )
        return JsonResponse({
            "status": "success",
            "redirect_url": blog.get_absolute_url()
        })
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)
