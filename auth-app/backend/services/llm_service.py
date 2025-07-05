import json
import os
import time
import random
from typing import Dict, Optional, Tuple
import logging
from datetime import datetime
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Use modern OpenAI v1.x client
from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        # Initialize OpenAI client
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            self.client = None
        else:
            try:
                # Use modern OpenAI v1.x client
                self.client = OpenAI(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None

        # Configuration from environment variables
        self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "500"))
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum 1 second between requests

    def detect_book_series(
        self, book_name: str, book_author: str
    ) -> Tuple[bool, Optional[Dict], Dict]:
        """
        Detect if book is part of series and get next book recommendation

        Returns:
            (success: bool, parsed_response: Optional[Dict], metadata: Dict)
        """
        if not self.client:
            return (
                False,
                None,
                {
                    "error": "OpenAI API key not configured",
                    "timestamp": datetime.utcnow(),
                },
            )

        # Rate limiting
        self._rate_limit()

        prompt = self._build_series_prompt(book_name, book_author)

        try:

            # Use modern OpenAI v1.x API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a book recommendation expert specializing in book series identification. Always respond with valid JSON only.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            raw_response = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens

            # Parse JSON response
            parsed = self._parse_llm_response(raw_response)

            if parsed is None:
                raise ValueError(f"Invalid JSON response: {raw_response}")

            # Validate response structure
            if not self._validate_response(parsed):
                raise ValueError(f"Invalid response structure: {parsed}")

            metadata = {
                "model": self.model,
                "prompt": prompt,
                "raw_response": raw_response,
                "parsed_response": parsed,
                "tokens_used": tokens_used,
                "timestamp": datetime.utcnow(),
                "success": True,
            }

            return True, parsed, metadata

        except Exception as e:
            error_type = "unknown_error"
            error_message = str(e)

            # Handle specific OpenAI errors
            if "rate limit" in error_message.lower():
                error_type = "rate_limit"
            elif "timeout" in error_message.lower():
                error_type = "timeout"
            elif "api" in error_message.lower():
                error_type = "api_error"
            return (
                False,
                None,
                {
                    "error": error_message,
                    "type": error_type,
                    "timestamp": datetime.utcnow(),
                },
            )

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return (
                False,
                None,
                {
                    "error": f"Invalid JSON response: {str(e)}",
                    "type": "json_error",
                    "timestamp": datetime.utcnow(),
                },
            )

    def _build_series_prompt(self, book_name: str, book_author: str) -> str:
        """Build the prompt for series detection"""
        # Clean book name and author
        clean_book_name = self._clean_text(book_name)
        clean_author = self._clean_text(book_author) if book_author else "Unknown"

        prompt = f"""We are a book recommendation store. For the book titled '{clean_book_name}' by {clean_author}, please identify if this book is part of a series and recommend the next book in that series. Only respond if there is an actual series with a confirmed next book available.

IMPORTANT:
1. Respond with valid JSON only. No additional text or explanations.
2. For the next book title, include the series name when appropriate (e.g., "The Hunger Games: Catching Fire", "Harry Potter and the Chamber of Secrets")
3. Be specific and use the full official title.

Response format (JSON only):
{{
  "is_series": boolean,
  "series_name": "string",
  "next_book": {{
    "title": "string",
    "author": "string",
    "description": "string",
    "order_in_series": number
  }},
  "confidence": number (0-1)
}}

If not part of a series or no next book exists, respond with: {{"is_series": false}}

Book: {clean_book_name}
Author: {clean_author}"""

        return prompt

    def _parse_llm_response(self, raw_response: str) -> Optional[Dict]:
        """Parse and clean the LLM response"""
        try:
            # Remove common prefixes/suffixes that might break JSON
            cleaned_response = raw_response.strip()

            # Remove markdown code blocks if present
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]

            cleaned_response = cleaned_response.strip()

            # Try to find JSON content using regex as fallback
            json_match = re.search(r"\{.*\}", cleaned_response, re.DOTALL)
            if json_match:
                cleaned_response = json_match.group()

            # Parse JSON
            parsed = json.loads(cleaned_response)
            return parsed

        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON response: {raw_response}")
            return None
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return None

    def _validate_response(self, parsed: Dict) -> bool:
        """Validate the structure of the parsed response"""
        try:
            # Check for required fields
            if "is_series" not in parsed:
                return False

            # If it's not a series, that's valid
            if not parsed["is_series"]:
                return True

            # If it is a series, check required fields
            required_fields = ["series_name", "next_book", "confidence"]
            for field in required_fields:
                if field not in parsed:
                    return False

            # Validate next_book structure
            next_book = parsed["next_book"]
            if not isinstance(next_book, dict):
                return False

            next_book_required = ["title", "author"]
            for field in next_book_required:
                if field not in next_book or not next_book[field]:
                    return False

            # Validate confidence score
            confidence = parsed.get("confidence", 0)
            if (
                not isinstance(confidence, (int, float))
                or confidence < 0
                or confidence > 1
            ):
                parsed["confidence"] = 0.8  # Default confidence

            return True

        except Exception as e:
            logger.error(f"Error validating response: {e}")
            return False

    def _clean_text(self, text: str) -> str:
        """Clean text for safe use in prompts"""
        if not text:
            return ""

        # Remove potential prompt injection attempts
        cleaned = text.replace('"', "'").replace("\n", " ").replace("\r", " ")

        # Limit length to prevent token overflow
        if len(cleaned) > 200:
            cleaned = cleaned[:200] + "..."

        return cleaned.strip()

    def _rate_limit(self, attempt=0):
        """Exponential backoff with jitter for rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        # Calculate delay with exponential backoff and jitter
        if attempt == 0:
            # Initial delay with jitter
            base_delay = max(self.min_request_interval - time_since_last, 0)
            delay = base_delay + random.uniform(0.5, 1.5)
        else:
            # Exponential backoff with jitter for retries
            base_delay = min(2**attempt, 8)  # Max 8 seconds
            delay = random.uniform(base_delay * 0.5, base_delay * 1.5)

        if delay > 0:
            time.sleep(delay)

        self.last_request_time = time.time()


# Global instance - Initialize lazily to avoid startup issues
llm_service = None


def get_llm_service():
    """Get or create LLM service instance"""
    global llm_service
    if llm_service is None:
        llm_service = LLMService()
    return llm_service
