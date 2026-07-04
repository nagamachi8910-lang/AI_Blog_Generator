# services/render package initializer
from .renderer import render_section, RenderDescriptor, get_renderer_for_type

__all__ = [
    "render_section",
    "RenderDescriptor",
    "get_renderer_for_type",
]
