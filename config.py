# ==============================================================================
# config.py - Settings for TradeGenie AI Trading Assistant
# ==============================================================================

import os
import logging
from telegram import Update # Required for Update.ALL_TYPES for ALLOWED_UPDATES

# --- 1. API Keys & Endpoints ---
# It's best practice to load sensitive keys from environment variables.
# Provide default values here for local development if desired, but for
# production, ensure these are set in your environment or a .env file.
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "TELEGRAM_TOKEN") # Replace with your bot token
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "YOUR_CLAUDE_API_KEY") # Replace with your Claude API key
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "DEEPSEEK_API_KEY") # Replace with your DeepSeek API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "OPENAI_API_KEY") # Replace with your OpenAI API key

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# --- 2. LLM Model Configurations ---
# Claude est conservé pour la modularité, même s'il n'est pas utilisé directement dans le flux actuel
CLAUDE_MODEL = "claude-3-haiku-20240307" 
DEEPSEEK_MODEL = "deepseek-chat" # Common model name for DeepSeek chat
CHATGPT_MODEL = "gpt-4o" # Use a vision-capable model like gpt-4o or gpt-4-turbo

# --- 3. Image & File Handling ---
MAX_IMAGE_SIZE_MB = 2 # Max file size for images to be sent to LLMs
MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024

# --- 4. Trading Parameters ---
DEFAULT_RISK_PERCENT = 1.0 # Default risk per trade, in percentage
DEFAULT_LOT_SIZE_MULTIPLIER = 100000 # Standard lot size for forex/futures (e.g., 100,000 units for forex)

# Asset Definitions (extendable later)
SUPPORTED_ASSETS = ["XAUUSD", "EURUSD"]
# Define pip values per 1 standard lot for calculating risk
# Example: For XAUUSD, 1 lot = 100 oz. If 1 pip = $0.10/oz, then 1 pip/lot = $10.
# For EURUSD, 1 lot = 100,000 units. If 1 pip = $0.0001, then 1 pip/lot = $10.
ASSET_PIP_VALUES = {
    "XAUUSD": 10,
    "EURUSD": 10,
}

# Module Definitions (extendable later)
SUPPORTED_MODULES = ["SWING", "AMD"]

# --- 5. Logging Configuration ---
LOGGING_LEVEL = logging.INFO
LOGGING_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# --- 6. Telegram Bot Settings ---
# Update types to allow (optimizes webhook/polling traffic)
ALLOWED_UPDATES = [Update.MESSAGE, Update.EDITED_MESSAGE, Update.CHANNEL_POST, Update.EDITED_CHANNEL_POST, Update.CHOSEN_INLINE_RESULT, Update.INLINE_QUERY, Update.CALLBACK_QUERY]

# --- 7. Conversation States (for Telegram Bot API's ConversationHandler) ---
# These are symbolic constants to manage the flow of interaction.
# Using consecutive integers for states is a common practice.
(
    GET_TRADE_PARAMS, # Initial state to get Asset, Module, Capital
    WAITING_H4_IMAGE,
    WAITING_H1_IMAGE,
    WAITING_M15_IMAGE, # For AMD module
    # Add more states here as the bot complexity grows
) = range(4) # Start range from a higher number if conflicts are possible, or use a specific range.

# --- 8. Paths to Prompts (within the 'prompts/' directory) ---
PROMPT_DIR = "prompts/" # Relative path to the prompts folder

# --- Claude Prompts (conservés pour la modularité future) ---
CLAUDE_SWING_VISION_PROMPT_PATH = os.path.join(PROMPT_DIR, "claude_swing_vision.txt")
CLAUDE_AMD_VISION_PROMPT_PATH = os.path.join(PROMPT_DIR, "claude_amd_vision.txt")
CLAUDE_BASE_SYSTEM_PROMPT_PATH = os.path.join(PROMPT_DIR, "claude_base_system.txt")

# --- DeepSeek Prompts ---
DEEPSEEK_SWING_PROMPT_PATH = os.path.join(PROMPT_DIR, "deepseek_swing.txt")
DEEPSEEK_AMD_PROMPT_PATH = os.path.join(PROMPT_DIR, "deepseek_amd.txt")
DEEPSEEK_BASE_SYSTEM_PROMPT_PATH = os.path.join(PROMPT_DIR, "deepseek_base_system.txt")

# --- ChatGPT Prompts (maintenant utilisés pour l'analyse vision) ---
CHATGPT_SWING_VISION_PROMPT_PATH = os.path.join(PROMPT_DIR, "chatgpt_swing_vision.txt")
CHATGPT_AMD_VISION_PROMPT_PATH = os.path.join(PROMPT_DIR, "chatgpt_amd_vision.txt")
CHATGPT_BASE_SYSTEM_PROMPT_PATH = os.path.join(PROMPT_DIR, "chatgpt_base_system.txt") # General system prompt for ChatGPT

# --- 9. Data Management ---
USER_DATA_CLEANUP_INTERVAL_SECONDS = 3600 # Clean up user data every hour (1 hour)

print("✅ Config loaded.")