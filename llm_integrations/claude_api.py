# ==============================================================================
# llm_integrations/claude_api.py - Functions for Interacting with Claude API
# ==============================================================================

import asyncio
import logging
import os
from typing import List, Dict, Union

import anthropic

# Import necessary configurations
from config import (
    CLAUDE_API_KEY,
    CLAUDE_MODEL,
    MAX_IMAGE_SIZE_BYTES, # Relevant for checking image size
    CLAUDE_BASE_SYSTEM_PROMPT_PATH,
    PROMPT_DIR # To load prompts dynamically
)
from utils.image_processing import image_to_base64 # To encode images

logger = logging.getLogger(__name__)

# Initialize Claude client globally for reusability
claude_client = None
if CLAUDE_API_KEY:
    try:
        claude_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
        logger.info("Claude client initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize Claude client: {e}")
else:
    logger.warning("CLAUDE_API_KEY is not set. Claude API functions will not work.")

# --- Helper to load prompts from files ---
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
CLAUDE_SYSTEM_PROMPT = ""
if CLAUDE_BASE_SYSTEM_PROMPT_PATH:
    CLAUDE_SYSTEM_PROMPT = _load_prompt_from_file(CLAUDE_BASE_SYSTEM_PROMPT_PATH)
    if CLAUDE_SYSTEM_PROMPT:
        logger.info("Claude base system prompt loaded.")
    else:
        logger.warning("Could not load Claude base system prompt from file.")


async def get_claude_vision_analysis(
    user_prompt: str,
    image_bytes_list: List[bytes],
    model: str = CLAUDE_MODEL,
    max_tokens: int = 1500,
    temperature: float = 0.3,
    system_prompt: str = CLAUDE_SYSTEM_PROMPT
) -> str:
    """
    Sends a prompt and image(s) to Anthropic's Claude 3 vision model for analysis.

    Args:
        user_prompt: The text prompt for Claude.
        image_bytes_list: A list of raw image bytes (e.g., JPEG, PNG) to send.
                          Each image will be converted to base64 PNG.
        model: The Claude model to use (default from config).
        max_tokens: The maximum number of tokens for the model's response.
        temperature: Controls randomness in generation. Lower is more deterministic.
        system_prompt: An optional system message to guide Claude's behavior.

    Returns:
        The text response from Claude, or an error message if the API call fails.
    """
    if not claude_client:
        return "❌ Error: Claude API key not configured."

    if not user_prompt:
        return "❌ Error: Cannot perform Claude analysis without a user prompt."
    
    messages_content: List[Dict[str, str]] = []

    # Add text prompt first
    messages_content.append({"type": "text", "text": user_prompt})

    # Add images
    for i, img_bytes in enumerate(image_bytes_list):
        if len(img_bytes) > MAX_IMAGE_SIZE_BYTES:
            logger.warning(f"Image {i+1} is too large ({len(img_bytes)} bytes) for Claude vision. Max {MAX_IMAGE_SIZE_BYTES} bytes. Skipping this image.")
            messages_content.append({"type": "text", "text": f"Warning: Image {i+1} was too large and was not processed."})
            continue

        try:
            base64_image = image_to_base64(img_bytes)
            messages_content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png", # We convert all to PNG
                    "data": base64_image
                }
            })
        except Exception as e:
            logger.error(f"Failed to encode image {i+1} for Claude: {e}")
            messages_content.append({"type": "text", "text": f"Error processing image {i+1} for vision analysis."})
    
    if not messages_content:
        return "❌ Error: No valid content (text or images) to send to Claude."

    try:
        # Construct the messages list for the API call
        messages = [{"role": "user", "content": messages_content}]
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})


        response = await claude_client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages
        )
        return response.content[0].text
    except anthropic.APIError as e:
        logger.error(f"Claude API Error: {e}")
        return f"❌ Claude API Error: {e.status_code} - {e.response.text}"
    except Exception as e:
        logger.error(f"An unexpected error occurred with Claude API: {e}")
        return f"❌ Unexpected Claude API error: {e}"