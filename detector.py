"""
Multi-device detection engine.
Identifies when the same account is accessed from different devices within a short time window.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from database import Database


async def check_multi_device(
    db: Database,
    telegram_id: int,
    phone: str,
    current_session: Dict[str, Any],
    current_session_id: int
) -> Dict[str, Any]:
    """
    Check if the current session indicates multi-device usage.
    
    Detection logic:
    - Find the latest session for the same Telegram ID OR same phone number
    - If found within last 60 seconds AND different device (based on super_fingerprint)
    - Then trigger alert
    
    Returns:
        dict with 'detected' (bool), 'previous_session' (dict or None), 'time_diff' (int)
    """
    # Get latest session for same Telegram ID (excluding current)
    previous_by_telegram = await db.get_latest_session_by_telegram(telegram_id, exclude_id=current_session_id)
    
    # Get latest session for same phone number (excluding current)
    previous_by_phone = await db.get_latest_session_by_phone(phone, exclude_id=current_session_id)
    
    # Choose the most recent of the two
    previous_session = None
    if previous_by_telegram and previous_by_phone:
        # Compare timestamps
        if previous_by_telegram["created_at"] > previous_by_phone["created_at"]:
            previous_session = previous_by_telegram
        else:
            previous_session = previous_by_phone
    elif previous_by_telegram:
        previous_session = previous_by_telegram
    elif previous_by_phone:
        previous_session = previous_by_phone
    
    # No previous session found
    if not previous_session:
        return {"detected": False, "previous_session": None, "time_diff": 0}
    
    # Calculate time difference
    current_time = datetime.fromisoformat(current_session["created_at"]) if isinstance(current_session["created_at"], str) else current_session["created_at"]
    prev_time = datetime.fromisoformat(previous_session["created_at"]) if isinstance(previous_session["created_at"], str) else previous_session["created_at"]
    
    # Ensure timezone-naive comparison (assuming UTC)
    if current_time.tzinfo:
        current_time = current_time.replace(tzinfo=None)
    if prev_time.tzinfo:
        prev_time = prev_time.replace(tzinfo=None)
    
    time_diff_seconds = int((current_time - prev_time).total_seconds())
    
    # Only detect if within 60 seconds
    if time_diff_seconds > 60:
        return {"detected": False, "previous_session": previous_session, "time_diff": time_diff_seconds}
    
    # Check if devices are different by comparing super fingerprints
    current_super_fp = current_session["super_fingerprint"]
    previous_super_fp = previous_session["super_fingerprint"]
    
    # Also compare IP, OS, browser as additional indicators
    ip_different = current_session["ip"] != previous_session["ip"]
    os_different = current_session["os"] != previous_session["os"]
    browser_different = current_session["browser"] != previous_session["browser"]
    
    # Device is considered different if super fingerprint mismatches
    # OR if significant changes in IP, OS, and browser (fallback)
    is_different_device = (
        current_super_fp != previous_super_fp or
        (ip_different and os_different and browser_different)
    )
    
    if is_different_device:
        return {
            "detected": True,
            "previous_session": previous_session,
            "time_diff": time_diff_seconds
        }
    
    return {"detected": False, "previous_session": previous_session, "time_diff": time_diff_seconds}