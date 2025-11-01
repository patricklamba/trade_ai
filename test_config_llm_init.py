# TradeGenie/test_config_llm_init.py

import os
import sys
import asyncio
import logging

# Add current directory to the Python path to allow imports from config and llm_integrations
current_script_dir = os.path.dirname(os.path.abspath(__file__))
if current_script_dir not in sys.path:
    sys.path.append(current_script_dir)

from config import (
    TELEGRAM_TOKEN, DEEPSEEK_API_KEY, OPENAI_API_KEY,
    DEEPSEEK_MODEL, CHATGPT_MODEL,
    LOGGING_LEVEL, LOGGING_FORMAT
)
# IMPORTS CORRIGÉS
import llm_integrations.deepseek_api # Importe le module entier
import llm_integrations.chatgpt_api # Importe le module entier pour que le client s'initialise

# Accède aux clients via le module qu'ils ont initialisé
openai_client_obj = llm_integrations.chatgpt_api.openai_client


# Setup minimal logging for this test script
logging.basicConfig(level=LOGGING_LEVEL, format=LOGGING_FORMAT)
logger = logging.getLogger(__name__)

async def test_llm_clients():
    logger.info("--- Starting LLM Client Initialization Test ---")

    # Test config values
    logger.info(f"TELEGRAM_TOKEN set: {'YES' if TELEGRAM_TOKEN and TELEGRAM_TOKEN != 'YOUR_TELEGRAM_BOT_TOKEN' else 'NO'}")
    logger.info(f"DEEPSEEK_API_KEY set: {'YES' if DEEPSEEK_API_KEY and DEEPSEEK_API_KEY != 'YOUR_DEEPSEEK_API_KEY' else 'NO'}")
    logger.info(f"OPENAI_API_KEY set: {'YES' if OPENAI_API_KEY and OPENAI_API_KEY != 'YOUR_OPENAI_API_KEY' else 'NO'}")

    
    # Test DeepSeek (pas de client objet global, juste la clé API)
    if DEEPSEEK_API_KEY and DEEPSEEK_API_KEY != 'YOUR_DEEPSEEK_API_KEY':
        logger.info(f"DeepSeek API key present. Model: {DEEPSEEK_MODEL}")
    else:
        logger.error("DeepSeek API key missing or default value used.")

    # Test OpenAI client
    if openai_client_obj:
        logger.info(f"OpenAI client initialized successfully. Model: {CHATGPT_MODEL}")
    else:
        logger.error("OpenAI client failed to initialize (check OPENAI_API_KEY in config.py).")

    logger.info("--- LLM Client Initialization Test Complete ---")


if __name__ == "__main__":
    asyncio.run(test_llm_clients())