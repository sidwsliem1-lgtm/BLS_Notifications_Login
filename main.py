"""
Main FastAPI application without subfolders.
All static files and templates are in the same directory.
"""

import hashlib
import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel, validator
from dotenv import load_dotenv

# Local imports
from database import Database
from bot import bot, dispatcher, send_alert_to_admins
from detector import check_multi_device

load_dotenv()

# Rate limiting storage
rate_limit_storage: Dict[str, list] = defaultdict(list)
RATE_LIMIT = 5
RATE_WINDOW = 60

db = Database()


class TrackingData(BaseModel):
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
        if not v or len(v) < 5:
            raise ValueError('Invalid phone number')
        return v

    @validator('telegram_id')
    def validate_telegram_id(cls, v):
        if v <= 0:
            raise ValueError('Invalid Telegram ID')
        return v


def generate_super_fingerprint(data: TrackingData) -> str:
    fingerprint_string = f"{data.fingerprint}|{data.user_agent}|{data.screen}|{data.timezone}|{data.canvas}|{data.webgl}"
    return hashlib.sha256(fingerprint_string.encode()).hexdigest()


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host


def check_rate_limit(ip: str) -> bool:
    now = time.time()
    requests = rate_limit_storage[ip]
    rate_limit_storage[ip] = [t for t in requests if now - t < RATE_WINDOW]
    if len(rate_limit_storage[ip]) >= RATE_LIMIT:
        return False
    rate_limit_storage[ip].append(now)
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🟢 Starting application...")
    await db.init_db()
    print("✅ Database initialized")
    bot_task = asyncio.create_task(dispatcher.start_polling(bot))
    print("✅ Telegram bot started")
    yield
    print("🔴 Shutting down...")
    bot_task.cancel()
    await bot.session.close()
    await db.close()
    print("✅ Cleanup complete")


app = FastAPI(lifespan=lifespan, title="Anti Multi-Device Detection")


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main HTML page."""
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/style.css")
async def serve_css():
    """Serve CSS file."""
    return FileResponse("style.css", media_type="text/css")


@app.get("/app.js")
async def serve_js():
    """Serve JS file."""
    return FileResponse("app.js", media_type="application/javascript")


@app.post("/track")
async def track_device(request: Request, data: TrackingData):
    client_ip = get_client_ip(request)
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait.")
    
    super_fingerprint = generate_super_fingerprint(data)
    
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
    
    session_id = await db.insert_session(session_data)
    detection_result = await check_multi_device(db, data.telegram_id, data.phone, session_data, session_id)
    
    if detection_result["detected"]:
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
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)