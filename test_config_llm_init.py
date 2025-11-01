# TradeGenie/test_config_llm_init.py

import os
import sys
import asyncio
import logging

# Add current directory to the Python path to allow imports from config and llm_integrations
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import (
    TELEGRAM_TOKEN, CLAUDE_API_KEY, DEEPSEEK_API_KEY, OPENAI_API_KEY,
    CLAUDE_MODEL, DEEPSEEK_MODEL, CHATGPT_MODEL,
    LOGGING_LEVEL, LOGGING_FORMAT
)
from llm_integrations.claude_api import claude_client # Import the global client
from llm_integrations.deepseek_api import logger as deepseek_logger # To get DeepSeek's specific logger
from llm_integrations.chatgpt_api import openai_client # Import the global client

# Setup minimal logging for this test script
logging.basicConfig(level=LOGGING_LEVEL, format=LOGGING_FORMAT)
logger = logging.getLogger(__name__)

async def test_llm_clients():
    logger.info("--- Starting LLM Client Initialization Test ---")

    # Test config values
    logger.info(f"TELEGRAM_TOKEN set: {'YES' if TELEGRAM_TOKEN else 'NO'}")
    logger.info(f"CLAUDE_API_KEY set: {'YES' if CLAUDE_API_KEY else 'NO'}")
    logger.info(f"DEEPSEEK_API_KEY set: {'YES' if DEEPSEEK_API_KEY else 'NO'}")
    logger.info(f"OPENAI_API_KEY set: {'YES' if OPENAI_API_KEY else 'NO'}")

    # Test Claude client
    if claude_client:
        logger.info(f"Claude client initialized successfully. Model: {CLAUDE_MODEL}")
    else:
        logger.error("Claude client failed to initialize (check CLAUDE_API_KEY).")

    # Test DeepSeek (we don't have a global client due to it being requests, but API key check is enough)
    if DEEPSEEK_API_KEY:
        logger.info(f"DeepSeek API key present. Model: {DEEPSEEK_MODEL}")
    else:
        logger.error("DeepSeek API key missing.")


    # Test OpenAI client
    if openai_client:
        logger.info(f"OpenAI client initialized successfully. Model: {CHATGPT_MODEL}")
    else:
        logger.error("OpenAI client failed to initialize (check OPENAI_API_KEY).")

    logger.info("--- LLM Client Initialization Test Complete ---")


if __name__ == "__main__":
    # Use asyncio.run for top-level async function
    asyncio.run(test_llm_clients())