import json
from typing import List


class ParsedSection:
    def __init__(
        self,
        section_type: str,
        heading: str,
        content: str,
        order: int,
        metadata: dict = None,
        generation_metadata: dict = None
    ):
        self.section_type = section_type
        self.heading = heading
        self.content = content
        self.order = order
        self.metadata = metadata or {}
        self.generation_metadata = generation_metadata or {}


class ParsedBlog:
    def __init__(self, title: str, summary: str, sections: List[ParsedSection]):
        self.title = title
        self.summary = summary
        self.sections = sections


def parse_blog_response(raw_text: str) -> ParsedBlog:
    """
    Transforms validated JSON data into ParsedBlog and ParsedSection model outputs.
    Target JSON validation must be pre-performed using validate_response_structure.
    """
    cleaned = (raw_text or "").strip()
    if not cleaned:
        raise ValueError("Cannot parse response: text is empty.")

    data = json.loads(cleaned)
    title = data.get("title", "")
    summary = data.get("summary", "")
    sections_data = data.get("sections", [])

    parsed_sections = []
    for sec in sections_data:
        parsed_sections.append(
            ParsedSection(
                section_type=sec["type"],
                heading=sec.get("heading") or "",
                content=sec.get("content") or "",
                order=sec["order"],
                metadata=sec.get("metadata") or {},
                # Save metadata and section definition as generation_metadata for regeneration
                generation_metadata={"raw_section": sec}
            )
        )

    return ParsedBlog(title=title, summary=summary, sections=parsed_sections)
