# ==============================================================================
# utils/risk_management.py - Trading Risk Management Functions for TradeGenie
# ==============================================================================

import logging
from typing import Dict

# Import configuration settings for asset-specific values
from config import ASSET_PIP_VALUES, DEFAULT_LOT_SIZE_MULTIPLIER

logger = logging.getLogger(__name__)

def calculate_position_size(
    account_capital: float,
    risk_percent: float,
    stop_loss_pips: float,
    asset_symbol: str,
    pip_value_per_lot: float = None # Optional: override config pip value
) -> float:
    """
    Calculates the appropriate position size (in lots) based on a
    percentage of account capital risked, stop loss distance in pips,
    and the asset's pip value.

    Args:
        account_capital: The total trading capital in the account (e.g., $100,000).
        risk_percent: The percentage of account capital to risk per trade (e.g., 1.0 for 1%).
                       This should be a direct percentage value (e.g., 1.0, not 0.01).
        stop_loss_pips: The distance of the Stop Loss from the entry price, in pips.
        asset_symbol: The symbol of the asset being traded (e.g., "XAUUSD", "EURUSD").
        pip_value_per_lot: Optional. Override the default pip value per lot from config.

    Returns:
        The calculated position size in standard lots (e.g., 0.5, 1.25 lots).
        Returns 0.0 if calculation is impossible (e.g., zero stop loss pips).
    """
    if stop_loss_pips <= 0:
        logger.warning(f"Stop Loss 'pips' must be positive. Received {stop_loss_pips}. Returning 0 position size.")
        return 0.0

    if account_capital <= 0:
        logger.warning(f"Account capital must be positive. Received {account_capital}. Returning 0 position size.")
        return 0.0

    if risk_percent <= 0:
        logger.warning(f"Risk percentage must be positive. Received {risk_percent}. Returning 0 position size.")
        return 0.0

    # Get pip value for the specific asset
    if pip_value_per_lot is None:
        actual_pip_value = ASSET_PIP_VALUES.get(asset_symbol.upper())
        if actual_pip_value is None:
            logger.error(f"Pip value not defined for asset '{asset_symbol}' in config. "
                         "Cannot calculate position size. Returning 0.0.")
            return 0.0
    else:
        actual_pip_value = pip_value_per_lot

    # Calculate monetary risk amount
    risk_amount = account_capital * (risk_percent / 100)

    # Calculate total risk in currency per lot
    # e.g., if 1 pip costs $10 per lot, and SL is 20 pips, then 1 lot risks $200.
    risk_per_lot_at_sl = stop_loss_pips * actual_pip_value

    if risk_per_lot_at_sl == 0: # Avoid division by zero if somehow actual_pip_value was 0.
        logger.warning("Calculated risk per lot at SL is zero. Returning 0 position size.")
        return 0.0

    # Position size in lots
    position_size_lots = risk_amount / risk_per_lot_at_sl

    logger.info(f"Position size calculated: Capital=${account_capital:,.2f}, Risk={risk_percent}%, "
                f"SL={stop_loss_pips} pips, Asset={asset_symbol}, PipValue/Lot=${actual_pip_value}/pip "
                f"-> Position Size={position_size_lots:.2f} lots.")

    # Return rounded to 2 decimal places, typical for lots
    return round(position_size_lots, 2)
