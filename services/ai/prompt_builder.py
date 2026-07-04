from .schema import JSON_SCHEMA_INSTRUCTIONS


class Prompt:
    def __init__(
        self,
        system_instruction: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_output_tokens: int = 2048
    ):
        self.system_instruction = system_instruction
        self.user_prompt = user_prompt
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens

    def __str__(self):
        return f"System Instructions: {self.system_instruction}\nUser Prompt: {self.user_prompt}"


class PromptBuilder:
    @staticmethod
    def build_blog_prompt(topic: str, tone: str, title: str = None) -> Prompt:
        system_instruction = (
            "You are a professional blog generator. Your task is to output a single, complete, "
            "and valid JSON object. You must strictly adhere to the following schema constraints:\n"
            f"{JSON_SCHEMA_INSTRUCTIONS}\n"
            "Return only raw JSON. Do not include markdown code block wraps (like ```json) or any preamble."
        )
        user_prompt = f"Generate a blog about topic: '{topic}' with a tone of '{tone}'."
        if title:
            user_prompt += f" Incorporate this title suggestion: '{title}'."
            
        return Prompt(
            system_instruction=system_instruction,
            user_prompt=user_prompt,
            temperature=0.7,
            max_output_tokens=3000
        )
