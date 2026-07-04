from abc import ABC, abstractmethod
from typing import List, Dict, Any
from apps.blogs.models import BlogSection, BlogImage
from .table_parser import parse_markdown_table


class RenderDescriptor:
    """
    A descriptor object holding template mappings and variables context
    returned for clean decoupling of rendering details.
    """
    def __init__(self, template_name: str, context: Dict[str, Any]):
        self.template_name = template_name
        self.context = context

    def render(self) -> str:
        """
        Loads the template and returns a raw HTML string.
        """
        from django.template.loader import render_to_string
        return render_to_string(self.template_name, self.context).strip()


class BaseSectionRenderer(ABC):
    @abstractmethod
    def get_descriptor(self, section: BlogSection, images: List[BlogImage]) -> RenderDescriptor:
        """
        Abstract method returning a RenderDescriptor object for each section.
        """
        pass


class HeadingRenderer(BaseSectionRenderer):
    def get_descriptor(self, section: BlogSection, images: List[BlogImage]) -> RenderDescriptor:
        return RenderDescriptor(
            template_name="blogs/partials/section_heading.html",
            context={
                "section": section,
                "heading": section.heading,
                "content": section.content,
                "images": images,
                "metadata": section.metadata or {}
            }
        )


class ParagraphRenderer(BaseSectionRenderer):
    def get_descriptor(self, section: BlogSection, images: List[BlogImage]) -> RenderDescriptor:
        return RenderDescriptor(
            template_name="blogs/partials/section_paragraph.html",
            context={
                "section": section,
                "heading": section.heading,
                "content": section.content,
                "images": images,
                "metadata": section.metadata or {}
            }
        )


class CodeRenderer(BaseSectionRenderer):
    def get_descriptor(self, section: BlogSection, images: List[BlogImage]) -> RenderDescriptor:
        metadata = section.metadata or {}
        # Read syntax highlighting language from metadata keys 'language' or 'lang'
        language = metadata.get("language") or metadata.get("lang") or "text"
        return RenderDescriptor(
            template_name="blogs/partials/section_code.html",
            context={
                "section": section,
                "heading": section.heading,
                "content": section.content,
                "images": images,
                "language": language,
                "metadata": metadata
            }
        )


class TableRenderer(BaseSectionRenderer):
    def get_descriptor(self, section: BlogSection, images: List[BlogImage]) -> RenderDescriptor:
        headers, rows = parse_markdown_table(section.content)
        return RenderDescriptor(
            template_name="blogs/partials/section_table.html",
            context={
                "section": section,
                "heading": section.heading,
                "headers": headers,
                "rows": rows,
                "images": images,
                "metadata": section.metadata or {}
            }
        )


class QuoteRenderer(BaseSectionRenderer):
    def get_descriptor(self, section: BlogSection, images: List[BlogImage]) -> RenderDescriptor:
        return RenderDescriptor(
            template_name="blogs/partials/section_quote.html",
            context={
                "section": section,
                "heading": section.heading,
                "content": section.content,
                "images": images,
                "metadata": section.metadata or {}
            }
        )


class TipRenderer(BaseSectionRenderer):
    def get_descriptor(self, section: BlogSection, images: List[BlogImage]) -> RenderDescriptor:
        return RenderDescriptor(
            template_name="blogs/partials/section_tip.html",
            context={
                "section": section,
                "heading": section.heading,
                "content": section.content,
                "images": images,
                "metadata": section.metadata or {}
            }
        )


class WarningRenderer(BaseSectionRenderer):
    def get_descriptor(self, section: BlogSection, images: List[BlogImage]) -> RenderDescriptor:
        return RenderDescriptor(
            template_name="blogs/partials/section_warning.html",
            context={
                "section": section,
                "heading": section.heading,
                "content": section.content,
                "images": images,
                "metadata": section.metadata or {}
            }
        )


class FaqRenderer(BaseSectionRenderer):
    def get_descriptor(self, section: BlogSection, images: List[BlogImage]) -> RenderDescriptor:
        content = (section.content or "").strip()
        faq_items = []
        
        # Normalize FAQ data: parse Q: and A: markers
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        current_q = ""
        current_a = ""

        # Check if markers exist at all in any of the lines
        has_markers = any(
            line.lower().startswith(("q:", "question:", "a:", "answer:"))
            for line in lines
        )

        if not has_markers:
            faq_items.append({"question": section.heading or "Question", "answer": content})
        else:
            for line in lines:
                line_lower = line.lower()
                if line_lower.startswith("q:") or line_lower.startswith("question:"):
                    # Save previous Q&A block
                    if current_q and current_a:
                        faq_items.append({"question": current_q, "answer": current_a})
                        current_q, current_a = "", ""
                    
                    parts = line.split(":", 1)
                    current_q = parts[1].strip()
                elif line_lower.startswith("a:") or line_lower.startswith("answer:"):
                    parts = line.split(":", 1)
                    current_a = parts[1].strip()
                else:
                    # Accumulate multi-line responses
                    if current_a:
                        current_a += " " + line
                    elif current_q:
                        current_q += " " + line
                    else:
                        current_q = line

            if current_q or current_a:
                faq_items.append({"question": current_q or "Question", "answer": current_a or content})

        if not faq_items:
            faq_items.append({"question": section.heading or "Question", "answer": content})

        return RenderDescriptor(
            template_name="blogs/partials/section_faq.html",
            context={
                "section": section,
                "heading": section.heading,
                "faq_items": faq_items,
                "images": images,
                "metadata": section.metadata or {}
            }
        )


class SummaryRenderer(BaseSectionRenderer):
    def get_descriptor(self, section: BlogSection, images: List[BlogImage]) -> RenderDescriptor:
        return RenderDescriptor(
            template_name="blogs/partials/section_summary.html",
            context={
                "section": section,
                "heading": section.heading,
                "content": section.content,
                "images": images,
                "metadata": section.metadata or {}
            }
        )


# Registry of section-specific renderers
RENDERER_REGISTRY: Dict[str, BaseSectionRenderer] = {
    "heading": HeadingRenderer(),
    "paragraph": ParagraphRenderer(),
    "code": CodeRenderer(),
    "table": TableRenderer(),
    "quote": QuoteRenderer(),
    "tip": TipRenderer(),
    "warning": WarningRenderer(),
    "faq": FaqRenderer(),
    "summary": SummaryRenderer(),
}


def get_renderer_for_type(section_type: str) -> BaseSectionRenderer:
    sec_type = (section_type or "").lower().strip()
    if sec_type not in RENDERER_REGISTRY:
        raise ValueError(f"Unsupported section type: '{section_type}'")
    return RENDERER_REGISTRY[sec_type]


def render_section(section: BlogSection) -> str:
    """
    Orchestration entry: retrieves the renderer object from the registry, resolves
    local images associated with this section, builds a RenderDescriptor, and compiles HTML.
    """
    if not isinstance(section, BlogSection):
        raise TypeError("Input must be an instance of BlogSection.")

    renderer = get_renderer_for_type(section.section_type)
    images = list(section.section_images.all()) if hasattr(section, 'section_images') else []
    descriptor = renderer.get_descriptor(section, images)
    return descriptor.render()
