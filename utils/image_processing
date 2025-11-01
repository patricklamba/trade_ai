# ==============================================================================
# utils/image_processing.py - Image Utility Functions for TradeGenie
# ==============================================================================

import base64
from io import BytesIO
import logging
from PIL import Image

# Initialize logger for this module
logger = logging.getLogger(__name__)

def convert_image_to_png(image_bytes: bytes) -> bytes:
    """
    Converts an image from any format supported by Pillow to PNG format.
    Some LLMs prefer or require specific image formats like PNG.
    If conversion fails, the original bytes are returned, and a warning is logged.

    Args:
        image_bytes: The raw bytes of the input image.

    Returns:
        The bytes of the image in PNG format, or the original bytes if conversion fails.
    """
    try:
        # Open the image from bytes
        image = Image.open(BytesIO(image_bytes))

        # Create a BytesIO buffer to save the PNG image
        png_buffer = BytesIO()
        image.save(png_buffer, format='PNG')

        # Get the bytes from the buffer
        return png_buffer.getvalue()
    except Exception as e:
        logger.warning(f"Failed to convert image to PNG. Error: {e}. Returning original image bytes.")
        return image_bytes

def image_to_base64(image_bytes: bytes) -> str:
    """
    Converts image bytes (preferably PNG) into a Base64 encoded string.
    This is required for sending images to most LLM vision APIs.

    Args:
        image_bytes: The raw bytes of the image (e.g., from Telegram, already converted to PNG).

    Returns:
        A Base64 encoded string representation of the image.
    """
    try:
        # Ensure the image is in PNG format before encoding
        png_bytes = convert_image_to_png(image_bytes)
        encoded_string = base64.b64encode(png_bytes).decode('utf-8')
        return encoded_string
    except Exception as e:
        logger.error(f"Failed to encode image to Base64. Error: {e}. This might lead to LLM errors.")
        # Fallback: try to encode original bytes if PNG conversion also failed critically.
        return base64.b64encode(image_bytes).decode('utf-8')