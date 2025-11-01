# ==============================================================================
# llm_integrations/chatgpt_api.py - Functions for Interacting with OpenAI ChatGPT API
# ==============================================================================

import openai # We'll need to install this library
import logging
import os
from typing import List, Dict, Union

# Import necessary configurations
from config import (
    OPENAI_API_KEY, # We need to add this to config.py
    CHATGPT_MODEL,  # We need to add this to config.py
    MAX_IMAGE_SIZE_BYTES, # Relevant for checking image size for vision models
    CHATGPT_BASE_SYSTEM_PROMPT_PATH, # We need to add this to config.py
    PROMPT_DIR
)
from utils.image_processing import image_to_base64 # To encode images

logger = logging.getLogger(__name__)

# Initialize OpenAI client globally for reusability
openai_client = None
if OPENAI_API_KEY:
    try:
        openai_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY) # Use AsyncOpenAI for async operations
        logger.info("OpenAI client initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
else:
    logger.warning("OPENAI_API_KEY is not set. OpenAI API functions will not work.")

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
CHATGPT_SYSTEM_PROMPT = ""
if CHATGPT_BASE_SYSTEM_PROMPT_PATH:
    CHATGPT_SYSTEM_PROMPT = _load_prompt_from_file(CHATGPT_BASE_SYSTEM_PROMPT_PATH)
    if CHATGPT_SYSTEM_PROMPT:
        logger.info("ChatGPT base system prompt loaded.")
    else:
        logger.warning("Could not load ChatGPT base system prompt from file.")


async def get_chatgpt_vision_analysis(
    user_prompt: str,
    image_bytes_list: List[bytes],
    model: str = CHATGPT_MODEL,
    max_tokens: int = 1500,
    temperature: float = 0.3,
    system_prompt: str = CHATGPT_SYSTEM_PROMPT,
    detail: str = "high" # or "low", "auto" for vision models
) -> str:
    """
    Sends a prompt and image(s) to OpenAI's GPT-4 Turbo with Vision model for analysis.

    Args:
        user_prompt: The text prompt for ChatGPT.
        image_bytes_list: A list of raw image bytes (e.g., JPEG, PNG) to send.
                          Each image will be converted to base64 PNG.
        model: The ChatGPT model to use (default from config). Should be a vision-capable model like gpt-4o or gpt-4-turbo.
        max_tokens: The maximum number of tokens for the model's response.
        temperature: Controls randomness in generation. Lower is more deterministic.
        system_prompt: An optional system message to guide ChatGPT's behavior.
        detail: Specifies the detail level for image processing ("high", "low", or "auto").

    Returns:
        The text response from ChatGPT, or an error message if the API call fails.
    """
    if not openai_client:
        return "❌ Error: OpenAI API key not configured."

    if not user_prompt:
        return "❌ Error: Cannot perform ChatGPT analysis without a user prompt."
    
    # Constructing content for the message
    content_parts: List[Dict[str, Union[str, Dict]]] = []

    # Add text prompt first
    content_parts.append({"type": "text", "text": user_prompt})

    # Add images
    for i, img_bytes in enumerate(image_bytes_list):
        if len(img_bytes) > MAX_IMAGE_SIZE_BYTES:
            logger.warning(f"Image {i+1} is too large ({len(img_bytes)} bytes) for ChatGPT vision. Max {MAX_IMAGE_SIZE_BYTES} bytes. Skipping this image.")
            content_parts.append({"type": "text", "text": f"Warning: Image {i+1} was too large and was not processed."})
            continue

        try:
            base64_image = image_to_base64(img_bytes)
            content_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_image}",
                    "detail": detail
                }
            })
        except Exception as e:
            logger.error(f"Failed to encode image {i+1} for ChatGPT: {e}")
            content_parts.append({"type": "text", "text": f"Error processing image {i+1} for vision analysis."})
    
    if not content_parts:
        return "❌ Error: No valid content (text or images) to send to ChatGPT."

    try:
        # Construct the messages list for the API call
        messages = [{"role": "user", "content": content_parts}]
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})

        response = await openai_client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content
    except openai.APIError as e:
        logger.error(f"ChatGPT API Error: {e}")
        return f"❌ ChatGPT API Error: {e.status_code} - {e.response}"
    except Exception as e:
        logger.error(f"An unexpected error occurred with ChatGPT API: {e}")
        return f"❌ Unexpected ChatGPT API error: {e}"