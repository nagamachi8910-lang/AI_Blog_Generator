from .provider import ImagePrompt


class ImagePromptBuilder:
    @staticmethod
    def build_prompt(
        blog_title: str,
        blog_topic: str,
        section_heading: str,
        section_content: str,
        section_type: str = ""
    ) -> ImagePrompt:
        """
        Builds a context-aware ImagePrompt incorporating topic, title, heading, and content.
        Explicitly includes the section type in the final rendered prompt.
        """
        heading_part = f" for heading '{section_heading}'" if section_heading else ""
        type_part = f"section type '{section_type}'" if section_type else "section content"
        prompt_text = (
            f"An illustration representing {type_part}{heading_part} "
            f"in a blog post about '{blog_topic}' titled '{blog_title}'. "
            f"Context: {section_content[:150]}"
        ).strip()
        
        return ImagePrompt(prompt_text=prompt_text, section_type=section_type)
