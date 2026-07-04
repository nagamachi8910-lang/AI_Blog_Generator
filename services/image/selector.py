from django.conf import settings


class ImageSelector:
    def select_sections_for_images(self, blog) -> list:
        """
        Filters the blog's sections, selecting those eligible for image generation
        based on the configurable setting IMAGE_ELIGIBLE_SECTION_TYPES.
        """
        eligible_types = getattr(
            settings,
            "IMAGE_ELIGIBLE_SECTION_TYPES",
            ["paragraph", "tip", "warning"]
        )
        # Normalize casing
        eligible_set = {str(t).lower().strip() for t in eligible_types}
        
        # Return DB sections filtered by type list
        return list(blog.sections.filter(section_type__in=eligible_set))
