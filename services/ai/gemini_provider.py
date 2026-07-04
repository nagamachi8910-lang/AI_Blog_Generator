import time
import logging
from django.conf import settings
from google import genai
from google.genai import types
from google.genai.errors import APIError

from .provider import AIProvider, GenerationResponse
from .prompt_builder import Prompt
from .validator import validate_response_structure

logger = logging.getLogger(__name__)


class GeminiProvider(AIProvider):
    def __init__(self):
        self.api_key = getattr(settings, "GEMINI_API_KEY", None)
        self.default_model = getattr(settings, "GEMINI_DEFAULT_MODEL", "gemini-2.5-flash")
        self.max_retries = getattr(settings, "GEMINI_MAX_RETRIES", 3)
        self.retry_delay = getattr(settings, "GEMINI_RETRY_DELAY", 2.0)
        self.timeout = getattr(settings, "GEMINI_TIMEOUT", 30.0)

    def generate_content(self, prompt, model: str = None) -> GenerationResponse:
        """
        Invokes Google Gemini API to generate structured blog content.
        Uses exponential backoff for rate limits and server errors, and validates output.
        """
        if not self.api_key:
            logger.error("Gemini API execution failed: GEMINI_API_KEY is not configured.")
            raise ValueError("Gemini API key is not configured in settings.")

        # Cast prompt to object for structured field readings
        if not isinstance(prompt, Prompt):
            raise TypeError("Prompt must be an instance of services.ai.Prompt class.")

        model_name = model or self.default_model
        
        # 1. Initialize genai Client
        client = genai.Client(api_key=self.api_key, http_options={"timeout": int(self.timeout)})

        # 2. Build model configuration parameters
        config = types.GenerateContentConfig(
            system_instruction=prompt.system_instruction,
            temperature=prompt.temperature,
            max_output_tokens=prompt.max_output_tokens,
            response_mime_type="application/json",
        )

        raw_text = None
        
        # 3. Retry loop with exponential backoff
        for attempt in range(1, self.max_retries + 1):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt.user_prompt,
                    config=config
                )
                
                if not response or not response.text:
                    raise ValueError("Empty response received from Gemini API.")
                    
                raw_text = response.text
                break  # Successful response, break retry loop
                
            except APIError as e:
                # HTTP 400 or 403 indicate credentials or configuration error; fail immediately
                if e.code in (400, 403):
                    logger.error(f"Gemini credentials verification failed: HTTP {e.code}.")
                    raise ValueError("Authentication error: Invalid Gemini API key.") from e
                    
                # recoverable codes: 429 (rate limit) or >=500 (server errors)
                if e.code == 429 or (e.code and e.code >= 500):
                    if attempt == self.max_retries:
                        logger.error(f"Gemini API rate limited/failed at attempt {attempt}. Exhausted retries.")
                        raise
                        
                    sleep_time = self.retry_delay * (2 ** (attempt - 1))
                    logger.warning(f"Gemini API request throttled/failed (HTTP {e.code}). Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                    continue
                raise
                
            except Exception as e:
                # Catch connection timeouts or dns issues
                if attempt == self.max_retries:
                    logger.error(f"Gemini connection failed at attempt {attempt}. Exhausted retries: {str(e)}.")
                    raise
                    
                sleep_time = self.retry_delay * (2 ** (attempt - 1))
                logger.warning(f"Gemini network socket error: {type(e).__name__}. Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
                continue

        # 4. Perform final structural verification checks
        if not raw_text:
            raise ValueError("Failure in generating blog text: response empty.")
            
        validate_response_structure(raw_text)

        # 5. Pack into GenerationResponse subclass
        return GenerationResponse(raw_text, provider="gemini", model=model_name)
