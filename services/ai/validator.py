import json
from .schema import SUPPORTED_SECTION_TYPES, SCHEMA_VERSION, validate_content_by_type


def validate_response_structure(raw_text: str) -> None:
    """
    Validates that the raw response is a valid JSON object complying with
    versioned schemas, unique constraints (ids & orders), and type-specific rules.
    """
    content = (raw_text or "").strip()
    if not content:
        raise ValueError("Generated response is empty.")

    # 1. Parse JSON syntax
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format received: {str(e)}") from e

    if not isinstance(data, dict):
        raise ValueError("Root element of the JSON response must be an object.")

    # 2. Schema version verification
    if "schema_version" not in data:
        raise ValueError("Missing 'schema_version' field in root object.")
    if data["schema_version"] != SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported schema version: {data['schema_version']}. Expected '{SCHEMA_VERSION}'."
        )

    # 3. Required top-level fields
    for field in ("title", "summary", "sections"):
        if field not in data:
            raise ValueError(f"Missing required field '{field}' in JSON response.")
        
    if not isinstance(data["title"], str) or not data["title"].strip():
        raise ValueError("Field 'title' must be a non-empty string.")
        
    if not isinstance(data["summary"], str) or not data["summary"].strip():
        raise ValueError("Field 'summary' must be a non-empty string.")

    sections = data["sections"]
    if not isinstance(sections, list):
        raise ValueError("Field 'sections' must be a list.")
        
    if not sections:
        raise ValueError("Field 'sections' list cannot be empty.")

    # 4. Iterative element checks (uniqueness, type-checking, metadata checks)
    seen_ids = set()
    seen_orders = set()

    for idx, sec in enumerate(sections):
        if not isinstance(sec, dict):
            raise ValueError(f"Section at index {idx} must be a JSON object.")

        # Require id, order, type, content, metadata
        for field in ("id", "order", "type", "content", "metadata"):
            if field not in sec:
                raise ValueError(f"Section at index {idx} is missing required field '{field}'.")

        # Validate order type
        if not isinstance(sec["order"], int):
            raise ValueError(f"Section at index {idx} has non-integer 'order' value.")

        # Validate ID format & uniqueness
        sec_id = str(sec["id"]).strip()
        if not sec_id:
            raise ValueError(f"Section at index {idx} has an empty 'id'.")
        if sec_id in seen_ids:
            raise ValueError(f"Duplicate section ID detected: '{sec_id}'.")
        seen_ids.add(sec_id)

        # Validate order uniqueness
        order_val = sec["order"]
        if order_val in seen_orders:
            raise ValueError(f"Duplicate section order value detected: '{order_val}'.")
        seen_orders.add(order_val)

        # Validate section type
        sec_type = str(sec["type"]).strip().lower()
        if sec_type not in SUPPORTED_SECTION_TYPES:
            raise ValueError(f"Section '{sec_id}' has unsupported type '{sec_type}'.")

        # Validate metadata is a dict
        if not isinstance(sec["metadata"], dict):
            raise ValueError(f"Section '{sec_id}' metadata is not a JSON object.")

        # Validate content structure according to section type
        heading = sec.get("heading") or ""
        content = sec.get("content") or ""
        validate_content_by_type(sec_type, heading, content, sec["metadata"])
