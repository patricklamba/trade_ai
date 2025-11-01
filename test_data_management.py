# TradeGenie/test_data_management.py

import os
import sys
import time
import logging

# Add current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import cleanup_old_user_data
from config import USER_DATA_CLEANUP_INTERVAL_SECONDS, LOGGING_LEVEL, LOGGING_FORMAT

# Temporarily reduce cleanup interval for quick testing
TEMP_CLEANUP_INTERVAL = 1 # 1 second

# Setup minimal logging
logging.basicConfig(level=LOGGING_LEVEL, format=LOGGING_FORMAT)
logger = logging.getLogger(__name__)

def test_cleanup_old_user_data():
    logger.info("--- Starting Data Management Test ---")

    # Create a dummy user data store
    test_data_store = {}

    # Add old data
    test_data_store[1] = {'timestamp': time.time() - (TEMP_CLEANUP_INTERVAL + 10), 'capital': 10000}
    test_data_store[2] = {'timestamp': time.time() - (TEMP_CLEANUP_INTERVAL + 5), 'capital': 20000}
    
    # Add fresh data
    test_data_store[3] = {'timestamp': time.time(), 'capital': 30000}
    test_data_store[4] = {'timestamp': time.time() - (TEMP_CLEANUP_INTERVAL / 2), 'capital': 40000}

    logger.info(f"Initial data store: {list(test_data_store.keys())}")
    
    # Override the cleanup interval for this test to be very short
    old_interval = USER_DATA_CLEANUP_INTERVAL_SECONDS
    # Monkey patching the config directly for the test, not ideal in production, but fine for quick test
    # In a proper testing framework, you'd use unittest.mock.patch
    class MockConfig:
        USER_DATA_CLEANUP_INTERVAL_SECONDS = TEMP_CLEANUP_INTERVAL
    
    # Temporarily modify the config module's constant (this isn't super clean, but works for quick tests)
    import utils
    utils.data_management.USER_DATA_CLEANUP_INTERVAL_SECONDS = TEMP_CLEANUP_INTERVAL
    logger.warning(f"Temporarily setting cleanup interval to {TEMP_CLEANUP_INTERVAL}s for testing.")

    cleanup_old_user_data(test_data_store)

    logger.info(f"Data store after cleanup: {list(test_data_store.keys())}")

    # Assertions
    assert 1 not in test_data_store, "User 1 (old data) should have been cleaned up."
    assert 2 not in test_data_store, "User 2 (old data) should have been cleaned up."
    assert 3 in test_data_store, "User 3 (fresh data) should remain."
    assert 4 in test_data_store, "User 4 (fresh data) should remain."

    logger.info("Data cleanup test successful: Old data removed, fresh data retained.")
    
    # Restore original interval
    utils.data_management.USER_DATA_CLEANUP_INTERVAL_SECONDS = old_interval
    logger.warning("Restored original cleanup interval.")

    logger.info("--- Data Management Test Complete ---")

if __name__ == "__main__":
    test_cleanup_old_user_data()