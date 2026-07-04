SUPPORTED_SECTION_TYPES = {
    "heading",
    "paragraph",
    "code",
    "table",
    "quote",
    "tip",
    "warning",
    "faq",
    "summary"
}

SCHEMA_VERSION = "1.0.0"

JSON_SCHEMA_INSTRUCTIONS = """
Your output must be a single, valid JSON object with NO additional explanation, introduction, or conversational text.
Do not wrap your output in markdown code blocks (e.g. do not use ```json ... ``` tags).
The root JSON object MUST match the following specification:
{
  "schema_version": "1.0.0",
  "title": "Blog post title",
  "summary": "High-level summary of the entire blog post",
  "sections": [
    {
      "id": "unique-section-uuid-or-slug",
      "order": 1,
      "type": "heading|paragraph|code|table|quote|tip|warning|faq|summary",
      "heading": "Optional section heading",
      "content": "Paragraph content, markdown code block, pipe-separated table string, or blockquote text.",
      "metadata": {}
    }
  ]
}
"""


def validate_content_by_type(section_type: str, heading: str, content: str, metadata: dict) -> None:
    """
    Validates content fields depending on their specialized section type.
    """
    section_type = (section_type or "").lower().strip()
    content_str = (content or "").strip()
    
    if section_type == "heading":
        if not heading.strip() and not content_str:
            raise ValueError("Heading sections require either 'heading' or 'content' field to be populated.")
            
    elif section_type == "paragraph":
        if not content_str:
            raise ValueError("Paragraph section requires non-empty 'content' field.")
            
    elif section_type == "code":
        if not content_str:
            raise ValueError("Code section requires non-empty 'content' field.")
            
    elif section_type == "table":
        if not content_str:
            raise ValueError("Table section requires non-empty 'content' field.")
        if "|" not in content_str:
            raise ValueError("Table section content must be formatted as a Markdown table containing pipe ('|') separators.")
            
    elif section_type == "quote":
        if not content_str:
            raise ValueError("Quote section requires non-empty 'content' field.")
            
    elif section_type == "tip":
        if not content_str:
            raise ValueError("Tip section requires non-empty 'content' field.")
            
    elif section_type == "warning":
        if not content_str:
            raise ValueError("Warning shadow box section requires non-empty 'content' field.")
            
    elif section_type == "faq":
        if not content_str:
            raise ValueError("FAQ section requires non-empty 'content' field.")
        content_lower = content_str.lower()
        if "?" not in content_str and "q:" not in content_lower and "question" not in content_lower:
            raise ValueError("FAQ section content must contain question and answer markers (e.g. '?', 'Q:', or 'Question:').")
            
    elif section_type == "summary":
        if not content_str:
            raise ValueError("Summary section requires non-empty 'content' field.")
