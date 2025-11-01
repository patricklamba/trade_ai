# ==============================================================================
# utils/data_management.py - User Data Management Functions for TradeGenie
# ==============================================================================

import time
import logging
from typing import Dict, Any

# Import configuration settings
from config import USER_DATA_CLEANUP_INTERVAL_SECONDS

logger = logging.getLogger(__name__)

def cleanup_old_user_data(user_data_store: Dict[int, Dict[str, Any]]) -> None:
    """
    Cleans up old user conversation data from the provided dictionary.
    Data entries older than USER_DATA_CLEANUP_INTERVAL_SECONDS are removed.

    Args:
        user_data_store: The dictionary holding all user conversation data.
                         (e.g., the global 'user_conversation_data' from main.py)
    """
    current_time = time.time()
    users_to_delete = []

    for user_id, data in user_data_store.items():
        # Ensure 'timestamp' exists in data for cleanup
        if 'timestamp' in data and (current_time - data['timestamp']) > USER_DATA_CLEANUP_INTERVAL_SECONDS:
            users_to_delete.append(user_id)
    
    if users_to_delete:
        logger.info(f"Initiating cleanup of old user data. Found {len(users_to_delete)} users to remove.")
        for user_id in users_to_delete:
            del user_data_store[user_id]
            logger.info(f"Removed old data for user_id: {user_id}")
    else:
        logger.debug("No old user data found for cleanup.")