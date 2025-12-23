"""Configuration for LLM-based normalization."""

import os
from typing import Optional
from openai import OpenAI


def get_llm_client() -> Optional[OpenAI]:
    """
    Get AITunnel LLM client (OpenAI-compatible).
    
    Returns None if LLM normalization is disabled or config is missing.
    """
    use_llm = os.environ.get("USE_LLM_NORMALIZATION", "false").lower() == "true"
    
    if not use_llm:
        return None
    
    api_key = os.environ.get("AITUNNEL_API_KEY")
    if not api_key:
        print("Warning: USE_LLM_NORMALIZATION=true but AITUNNEL_API_KEY not set. Falling back to rule-based.")
        return None
    
    base_url = os.environ.get("AITUNNEL_BASE_URL", "https://api.aitunnel.ru/v1/")
    
    return OpenAI(
        api_key=api_key,
        base_url=base_url
    )


def get_llm_model() -> str:
    """Get the model name to use for LLM normalization."""
    return os.environ.get("AITUNNEL_MODEL", "deepseek-r1")


def get_batch_size() -> int:
    """Get the batch size for LLM requests."""
    try:
        return int(os.environ.get("LLM_BATCH_SIZE", "50"))  # Increased default from 40 to 50
    except ValueError:
        return 50


def get_max_workers() -> int:
    """Get maximum number of parallel workers for batch processing."""
    try:
        return int(os.environ.get("LLM_MAX_WORKERS", "5"))  # Max 5 parallel requests
    except ValueError:
        return 5


def get_request_timeout() -> int:
    """Get request timeout in seconds."""
    try:
        return int(os.environ.get("LLM_REQUEST_TIMEOUT", "120"))  # 2 minutes default
    except ValueError:
        return 120


def get_max_retries() -> int:
    """Get maximum number of retry attempts for failed requests."""
    try:
        return int(os.environ.get("LLM_MAX_RETRIES", "2"))  # 2 retries default
    except ValueError:
        return 2


def is_llm_enabled() -> bool:
    """Check if LLM normalization is enabled."""
    return os.environ.get("USE_LLM_NORMALIZATION", "false").lower() == "true"

