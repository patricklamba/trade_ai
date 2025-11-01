# ==============================================================================
# llm_integrations/deepseek_api.py - Functions for Interacting with DeepSeek API
# ==============================================================================

import logging
import requests
import os
import asyncio
from typing import List, Dict, Union

# Import necessary configurations
from config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_API_URL,
    DEEPSEEK_MODEL,
    DEEPSEEK_BASE_SYSTEM_PROMPT_PATH,
    PROMPT_DIR
)

logger = logging.getLogger(__name__)

# --- Helper to load prompts from files ---
# (Duplicated from claude_api.py for self-containment, but could be moved to utils if desired)
def _load_prompt_from_file(file_path: str) -> str:
    """Loads a prompt string from a given file path."""
    full_path = os.path.join(os.getcwd(), PROMPT_DIR, os.path.basename(file_path))
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.error(f"Prompt file not found: {full_path}")
        return ""
    except Exception as e:
        logger.error(f"Error loading prompt from {full_path}: {e}")
        return ""

# Load base system prompt once
DEEPSEEK_SYSTEM_PROMPT = ""
if DEEPSEEK_BASE_SYSTEM_PROMPT_PATH:
    DEEPSEEK_SYSTEM_PROMPT = _load_prompt_from_file(DEEPSEEK_BASE_SYSTEM_PROMPT_PATH)
    if DEEPSEEK_SYSTEM_PROMPT:
        logger.info("DeepSeek base system prompt loaded.")
    else:
        logger.warning("Could not load DeepSeek base system prompt from file.")


async def get_deepseek_chat_completion(
    user_prompt: str,
    model: str = DEEPSEEK_MODEL,
    max_tokens: int = 1000,
    temperature: float = 0.5,
    system_prompt: str = DEEPSEEK_SYSTEM_PROMPT,
    timeout: int = 60
) -> str:
    """
    Sends a prompt to DeepSeek Chat API for text generation.

    Args:
        user_prompt: The text prompt for DeepSeek.
        model: The DeepSeek model to use (default from config).
        max_tokens: The maximum number of tokens for the model's response.
        temperature: Controls randomness in generation. Lower is more deterministic.
        system_prompt: An optional system message to guide DeepSeek's behavior.
        timeout: Request timeout in seconds.

    Returns:
        The text response from DeepSeek, or an error message if the API call fails.
    """
    if not DEEPSEEK_API_KEY:
        return "❌ Error: DeepSeek API key not configured."
    
    if not user_prompt:
        return "❌ Error: Cannot perform DeepSeek analysis without a user prompt."

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    data = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        # "stream": False, # DeepSeek supports streaming, but for simplicity, we'll get full response
    }

    try:
        # requests.post is synchronous, but we can run it in a thread pool
        # to prevent blocking the asyncio event loop.
        # This is a common pattern for integrating sync libs into async code.
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None, # Use the default ThreadPoolExecutor
            lambda: requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=timeout)
        )
        
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        
        json_response = response.json()
        if 'choices' in json_response and len(json_response['choices']) > 0:
            return json_response['choices'][0]['message']['content']
        else:
            logger.error(f"DeepSeek response missing 'choices': {json_response}")
            return "❌ DeepSeek API Error: Malformed response."

    except requests.exceptions.HTTPError as e:
        logger.error(f"DeepSeek HTTP Error: {e.response.status_code} - {e.response.text}")
        return f"❌ DeepSeek HTTP Error: {e.response.status_code} - {e.response.text}"
    except requests.exceptions.ConnectionError as e:
        logger.error(f"DeepSeek Connection Error: {e}")
        return f"❌ DeepSeek Connection Error: Could not connect to API."
    except requests.exceptions.Timeout as e:
        logger.error(f"DeepSeek Timeout Error: {e}")
        return f"❌ DeepSeek Timeout: Request took too long."
    except requests.exceptions.RequestException as e:
        logger.error(f"DeepSeek Request Error: {e}")
        return f"❌ DeepSeek Request Error: {e}"
    except Exception as e:
        logger.error(f"An unexpected error occurred with DeepSeek API: {e}")
        return f"❌ Unexpected DeepSeek API error: {e}"