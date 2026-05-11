"""
Main FastAPI application with integrated Telegram bot.
Handles web interface, tracking endpoint, and bot lifecycle.
"""

import asyncio
import hashlib
import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, Request, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Local imports
from database import Database
from bot import bot, dispatcher, send_alert_to_admins
from detector import check_multi_device

# Configuration
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# Rate limiting storage
rate_limit_storage: Dict[str, list] = defaultdict(list)
RATE_LIMIT = 5  # requests per minute
RATE_WINDOW = 60  # seconds

# Initialize database
db = Database()


# Pydantic model for tracking data
class TrackingData(BaseModel):
    """Validation model for incoming tracking data."""
    telegram_id: int
    username: Optional[str] = ""
    full_name: str
    phone: str
    fingerprint: str
    user_agent: str
    os: str
    browser: str
    screen: str
    timezone: str
    language: str
    canvas: str
    webgl: str
    
    @validator('phone')
    def validate_phone(cls, v):
        """Basic phone validation."""
        if not v or len(v) < 5:
            raise ValueError('Invalid phone number')
        return v
    
    @validator('telegram_id')
    def validate_telegram_id(cls, v):
        if v <= 0:
            raise ValueError('Invalid Telegram ID')
        return v


def generate_super_fingerprint(data: TrackingData) -> str:
    """
    Generate a strong super fingerprint using multiple data points.
    Combines fingerprint.js visitorId, user agent, screen, timezone, canvas, and webgl.
    """
    fingerprint_string = f"{data.fingerprint}|{data.user_agent}|{data.screen}|{data.timezone}|{data.canvas}|{data.webgl}"
    return hashlib.sha256(fingerprint_string.encode()).hexdigest()


def get_client_ip(request: Request) -> str:
    """Extract real client IP address considering proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host


def check_rate_limit(ip: str) -> bool:
    """Check if IP has exceeded rate limit."""
    now = time.time()
    requests = rate_limit_storage[ip]
    # Clean old requests
    rate_limit_storage[ip] = [t for t in requests if now - t < RATE_WINDOW]
    if len(rate_limit_storage[ip]) >= RATE_LIMIT:
        return False
    rate_limit_storage[ip].append(now)
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan: create tables, start bot polling, cleanup.
    """
    print("🟢 Starting application...")
    
    # Initialize database tables
    await db.init_db()
    print("✅ Database initialized")
    
    # Start bot polling in background
    bot_task = asyncio.create_task(dispatcher.start_polling(bot))
    print("✅ Telegram bot started")
    
    yield
    
    # Shutdown
    print("🔴 Shutting down...")
    bot_task.cancel()
    await bot.session.close()
    await db.close()
    print("✅ Cleanup complete")


# Create FastAPI app
app = FastAPI(lifespan=lifespan, title="Anti Multi-Device Detection")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main web interface."""
    return templates.TemplateResponse("index.html", {"request": request, "base_url": BASE_URL})


@app.post("/track")
async def track_device(request: Request, data: TrackingData):
    """
    Track device information, store in database, and detect multi-device usage.
    """
    # Rate limiting
    client_ip = get_client_ip(request)
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait.")
    
    # Generate super fingerprint
    super_fingerprint = generate_super_fingerprint(data)
    
    # Prepare session data
    session_data = {
        "telegram_id": data.telegram_id,
        "username": data.username or "",
        "full_name": data.full_name,
        "phone": data.phone,
        "fingerprint": data.fingerprint,
        "super_fingerprint": super_fingerprint,
        "ip": client_ip,
        "user_agent": data.user_agent,
        "os": data.os,
        "browser": data.browser,
        "screen": data.screen,
        "timezone": data.timezone,
        "language": data.language,
        "canvas": data.canvas,
        "webgl": data.webgl,
    }
    
    # Save to database
    session_id = await db.insert_session(session_data)
    
    # Check for multi-device detection
    detection_result = await check_multi_device(db, data.telegram_id, data.phone, session_data, session_id)
    
    if detection_result["detected"]:
        # Send alert to admins
        await send_alert_to_admins(
            current_session=session_data,
            previous_session=detection_result["previous_session"],
            time_diff=detection_result["time_diff"]
        )
        return JSONResponse(content={
            "status": "warning",
            "message": "تم اكتشاف استخدام متعدد الأجهزة. تم إخطار المسؤولين.",
            "detected": True
        })
    
    return JSONResponse(content={
        "status": "success",
        "message": "تم تسجيل جهازك بنجاح",
        "detected": False
    })


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)