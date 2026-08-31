"""PII and Sensitive Data Scrubber for Logs and Traces."""

import re
from typing import Any, Dict, List, Union


class PIIScrubber:
    """Comprehensive regex-based scrubber for PII, secrets, and credentials."""

    PATTERNS = [
        # Google API Keys (AIza...)
        (re.compile(r"AIza[0-9A-Za-z\-_]{30,}"), "[REDACTED_GOOGLE_API_KEY]"),
        # OpenAI / Standard API Keys (sk-...)
        (re.compile(r"sk-[a-zA-Z0-9_\-]{20,}"), "[REDACTED_API_KEY]"),
        # Bearer / Auth tokens
        (re.compile(r"(?i)bearer\s+[a-zA-Z0-9_\-\.]{20,}"), "Bearer [REDACTED_TOKEN]"),
        # Email Addresses
        (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"), "[REDACTED_EMAIL]"),
        # Phone Numbers (US/International formats)
        (re.compile(r"\b(?:\+?(\d{1,3}))?[-. (]*(\d{3})[-. )]*(\d{3})[-. ]*(\d{4})\b"), "[REDACTED_PHONE]"),
        # Social Security Numbers (SSN)
        (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),
        # IPv4 Addresses
        (re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"), "[REDACTED_IP]"),
        # AWS Access Keys
        (re.compile(r"\b(AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY]"),
    ]

    SENSITIVE_KEY_NAMES = {
        "api_key",
        "apikey",
        "token",
        "secret",
        "password",
        "authorization",
        "auth",
        "private_key",
        "credentials",
    }

    @classmethod
    def scrub_text(cls, text: str) -> str:
        """Scrub sensitive patterns from a string."""
        if not isinstance(text, str):
            return str(text)
        
        scrubbed = text
        for pattern, replacement in cls.PATTERNS:
            scrubbed = pattern.sub(replacement, scrubbed)
        return scrubbed

    @classmethod
    def scrub_data(cls, data: Union[Dict[str, Any], List[Any], str, Any]) -> Any:
        """Recursively scrub dictionaries, lists, and strings."""
        if isinstance(data, dict):
            cleaned = {}
            for k, v in data.items():
                if any(sens in k.lower() for sens in cls.SENSITIVE_KEY_NAMES):
                    cleaned[k] = "[REDACTED_CREDENTIAL]"
                else:
                    cleaned[k] = cls.scrub_data(v)
            return cleaned
        elif isinstance(data, list):
            return [cls.scrub_data(item) for item in data]
        elif isinstance(data, str):
            return cls.scrub_text(data)
        else:
            return data
