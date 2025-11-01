# TradeGenie/test_image_processing.py

import os
import sys
import base64
import logging
from PIL import Image
from io import BytesIO

# Add current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.image_processing import convert_image_to_png, image_to_base64
from config import LOGGING_LEVEL, LOGGING_FORMAT

# Setup minimal logging
logging.basicConfig(level=LOGGING_LEVEL, format=LOGGING_FORMAT)
logger = logging.getLogger(__name__)

def create_dummy_jpeg() -> bytes:
    """Creates a small dummy JPEG image in memory."""
    img = Image.new('RGB', (100, 50), color = 'red')
    byte_arr = BytesIO()
    img.save(byte_arr, format='JPEG')
    return byte_arr.getvalue()

def test_image_processing():
    logger.info("--- Starting Image Processing Test ---")

    # Create a dummy JPEG image
    dummy_jpeg_bytes = create_dummy_jpeg()
    logger.info(f"Created dummy JPEG (size: {len(dummy_jpeg_bytes)} bytes).")

    # Test convert_image_to_png
    png_bytes = convert_image_to_png(dummy_jpeg_bytes)
    logger.info(f"Converted to PNG (size: {len(png_bytes)} bytes).")
    try:
        Image.open(BytesIO(png_bytes)).verify()
        logger.info("PNG bytes are valid.")
    except Exception as e:
        logger.error(f"PNG verification failed: {e}")
        assert False, "PNG conversion failed"

    # Test image_to_base64
    base64_string = image_to_base64(dummy_jpeg_bytes)
    logger.info(f"Encoded to Base64 (length: {len(base64_string)}).")
    # A simple check that it's a valid base64
    decoded_bytes = base64.b64decode(base64_string)
    if not decoded_bytes:
        logger.error("Base64 decoding failed or resulted in empty bytes.")
        assert False, "Base64 encoding failed"
    
    logger.info("Base64 encoding and decoding seems successful.")
    
    logger.info("--- Image Processing Test Complete ---")

if __name__ == "__main__":
    test_image_processing()
