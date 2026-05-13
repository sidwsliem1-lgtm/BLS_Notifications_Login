"""
Multi-device detection engine.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from database import Database


async def check_multi_device(
    db: Database,
    telegram_id: int,
    phone: str,
    current_session: Dict[str, Any],
    current_session_id: int
) -> Dict[str, Any]:
    previous_by_telegram = await db.get_latest_session_by_telegram(telegram_id, exclude_id=current_session_id)
    previous_by_phone = await db.get_latest_session_by_phone(phone, exclude_id=current_session_id)
    
    previous_session = None
    if previous_by_telegram and previous_by_phone:
        if previous_by_telegram["created_at"] > previous_by_phone["created_at"]:
            previous_session = previous_by_telegram
        else:
            previous_session = previous_by_phone
    elif previous_by_telegram:
        previous_session = previous_by_telegram
    elif previous_by_phone:
        previous_session = previous_by_phone
    
    if not previous_session:
        return {"detected": False, "previous_session": None, "time_diff": 0}
    
    current_time = datetime.fromisoformat(current_session["created_at"]) if isinstance(current_session["created_at"], str) else current_session["created_at"]
    prev_time = datetime.fromisoformat(previous_session["created_at"]) if isinstance(previous_session["created_at"], str) else previous_session["created_at"]
    
    if current_time.tzinfo:
        current_time = current_time.replace(tzinfo=None)
    if prev_time.tzinfo:
        prev_time = prev_time.replace(tzinfo=None)
    
    time_diff_seconds = int((current_time - prev_time).total_seconds())
    
    if time_diff_seconds > 60:
        return {"detected": False, "previous_session": previous_session, "time_diff": time_diff_seconds}
    
    current_super_fp = current_session["super_fingerprint"]
    previous_super_fp = previous_session["super_fingerprint"]
    ip_different = current_session["ip"] != previous_session["ip"]
    os_different = current_session["os"] != previous_session["os"]
    browser_different = current_session["browser"] != previous_session["browser"]
    
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