import json
from django.test import TestCase
from services.ai.validator import validate_response_structure
from services.ai.parser import parse_blog_response


class StructuredGenerationTests(TestCase):
    def setUp(self):
        super().setUp()
        self.valid_json = {
            "schema_version": "1.0.0",
            "title": "Clean Code Architecture",
            "summary": "This is a summary of best coding practices.",
            "sections": [
                {
                    "id": "intro-sec",
                    "order": 1,
                    "type": "heading",
                    "heading": "Introduction",
                    "content": "Clean architecture separates concerns.",
                    "metadata": {}
                },
                {
                    "id": "body-sec",
                    "order": 2,
                    "type": "paragraph",
                    "heading": "",
                    "content": "Keep business logic decoupled from frameworks.",
                    "metadata": {"length": 45}
                },
                {
                    "id": "summary-sec",
                    "order": 3,
                    "type": "summary",
                    "heading": "Summary",
                    "content": "A short recap of coding standards.",
                    "metadata": {}
                }
            ]
        }

    def test_successful_parsing(self):
        """
        Verify that a completely valid JSON structure passes validation and parses correctly.
        """
        raw_text = json.dumps(self.valid_json)
        # Should not raise any exception
        validate_response_structure(raw_text)
        
        parsed = parse_blog_response(raw_text)
        self.assertEqual(parsed.title, "Clean Code Architecture")
        self.assertEqual(parsed.summary, "This is a summary of best coding practices.")
        self.assertEqual(len(parsed.sections), 3)
        self.assertEqual(parsed.sections[0].heading, "Introduction")
        self.assertEqual(parsed.sections[1].section_type, "paragraph")

    def test_malformed_json_fails(self):
        """
        Verify that invalid/malformed JSON string triggers ValueError.
        """
        raw_text = "{ 'invalid_key': value } "
        with self.assertRaises(ValueError) as ctx:
            validate_response_structure(raw_text)
        self.assertIn("Invalid JSON format", str(ctx.exception))

    def test_root_not_object_fails(self):
        """
        Verify that JSON with a list root triggers ValueError.
        """
        raw_text = json.dumps(["schema_version", "1.0.0"])
        with self.assertRaises(ValueError) as ctx:
            validate_response_structure(raw_text)
        self.assertIn("must be an object", str(ctx.exception))

    def test_schema_version_validation(self):
        """
        Verify that missing or unsupported schema version values fail.
        """
        # Missing schema_version
        data = self.valid_json.copy()
        del data["schema_version"]
        with self.assertRaises(ValueError) as ctx:
            validate_response_structure(json.dumps(data))
        self.assertIn("Missing 'schema_version'", str(ctx.exception))

        # Unsupported schema version
        data = self.valid_json.copy()
        data["schema_version"] = "2.0.0"
        with self.assertRaises(ValueError) as ctx:
            validate_response_structure(json.dumps(data))
        self.assertIn("Unsupported schema version: 2.0.0", str(ctx.exception))

    def test_missing_required_top_level_fields(self):
        """
        Verify that missing title, summary, or sections fields trigger ValueError.
        """
        for field in ("title", "summary", "sections"):
            data = self.valid_json.copy()
            del data[field]
            with self.assertRaises(ValueError) as ctx:
                validate_response_structure(json.dumps(data))
            self.assertIn(f"Missing required field '{field}'", str(ctx.exception))

    def test_empty_sections_fails(self):
        """
        Verify that empty sections list triggers database validation failure.
        """
        data = self.valid_json.copy()
        data["sections"] = []
        with self.assertRaises(ValueError) as ctx:
            validate_response_structure(json.dumps(data))
        self.assertIn("sections' list cannot be empty", str(ctx.exception))

    def test_duplicate_ids_fails(self):
        """
        Verify that sections with duplicate ID tags trigger ValueError.
        """
        data = self.valid_json.copy()
        # Set duplicate section ID
        data["sections"][1]["id"] = "intro-sec"
        with self.assertRaises(ValueError) as ctx:
            validate_response_structure(json.dumps(data))
        self.assertIn("Duplicate section ID detected: 'intro-sec'", str(ctx.exception))

    def test_duplicate_order_values_fails(self):
        """
        Verify that duplicate section order numbers raise validation errors.
        """
        data = self.valid_json.copy()
        # Set duplicate order value
        data["sections"][1]["order"] = 1
        with self.assertRaises(ValueError) as ctx:
            validate_response_structure(json.dumps(data))
        self.assertIn("Duplicate section order value detected: '1'", str(ctx.exception))

    def test_unsupported_section_type_fails(self):
        """
        Verify that unsupported section types (e.g. video) trigger ValueError.
        """
        data = self.valid_json.copy()
        data["sections"][0]["type"] = "video"
        with self.assertRaises(ValueError) as ctx:
            validate_response_structure(json.dumps(data))
        self.assertIn("unsupported type 'video'", str(ctx.exception))

    def test_malformed_metadata_fails(self):
        """
        Verify that non-object metadata properties fail validation.
        """
        data = self.valid_json.copy()
        data["sections"][0]["metadata"] = "length: 30"
        with self.assertRaises(ValueError) as ctx:
            validate_response_structure(json.dumps(data))
        self.assertIn("metadata is not a JSON object", str(ctx.exception))

    def test_section_content_structure_validation_by_type(self):
        """
        Verify that type-specific content validation rule checks are triggered correctly.
        """
        # Paragraph with missing content
        data = self.valid_json.copy()
        data["sections"][1]["content"] = ""
        with self.assertRaises(ValueError) as ctx:
            validate_response_structure(json.dumps(data))
        self.assertIn("Paragraph section requires non-empty 'content'", str(ctx.exception))

        # Table block without pipes
        data = self.valid_json.copy()
        data["sections"][1]["type"] = "table"
        data["sections"][1]["content"] = "Header values: col1, col2, col3"
        with self.assertRaises(ValueError) as ctx:
            validate_response_structure(json.dumps(data))
        self.assertIn("Markdown table containing pipe ('|')", str(ctx.exception))

        # FAQ block without question markers
        data = self.valid_json.copy()
        data["sections"][1]["type"] = "faq"
        data["sections"][1]["content"] = "This is a statement. That is an answer."
        with self.assertRaises(ValueError) as ctx:
            validate_response_structure(json.dumps(data))
        self.assertIn("FAQ section content must contain question and answer markers", str(ctx.exception))
