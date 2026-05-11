"""
Telegram bot using aiogram.
Handles /start command, WebApp button, and admin notifications.
"""

import os
from typing import List
from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo, KeyboardButton, ReplyKeyboardMarkup
from dotenv import load_dotenv

load_dotenv()

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]
BASE_URL = os.getenv("BASE_URL", "https://your-domain.com")

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dispatcher = Dispatcher()


@dispatcher.message(lambda message: message.text == "/start")
async def start_command(message: types.Message):
    """
    Handle /start command.
    Sends a welcome message with a WebApp button.
    """
    welcome_text = """
🌟 *مرحباً بك في نظام الحماية*

يمكنك تسجيل جهازك بالضغط على الزر أدناه.
سيتم مراقبة استخدام حسابك عبر الأجهزة المختلفة.

*ملاحظة:* يتم تسجيل بيانات الجلسة لحماية حسابك من الاستخدام المتعدد غير المصرح به.
"""
    
    # Create WebApp button
    webapp_button = KeyboardButton(
        text="📱 تسجيل الدخول",
        web_app=WebAppInfo(url=BASE_URL)
    )
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[webapp_button]],
        resize_keyboard=True
    )
    
    await message.answer(
        welcome_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def send_alert_to_admins(current_session: dict, previous_session: dict, time_diff: int):
    """
    Send an alert message to all configured admins.
    Message is in Arabic as requested.
    """
    alert_message = f"""
⚠️ *اكتشاف استخدام متعدد*

👤 *الاسم:* {current_session.get('full_name', 'غير معروف')}
📱 *الرقم:* {current_session.get('phone', 'غير معروف')}
🆔 *Telegram ID:* {current_session.get('telegram_id', 'غير معروف')}

🌐 *IP القديم:* {previous_session.get('ip', 'غير معروف')}
🌐 *IP الجديد:* {current_session.get('ip', 'غير معروف')}

💻 *النظام القديم:* {previous_session.get('os', 'غير معروف')} | {previous_session.get('browser', 'غير معروف')}
💻 *النظام الجديد:* {current_session.get('os', 'غير معروف')} | {current_session.get('browser', 'غير معروف')}

🕒 *الوقت بين الجلسات:* {time_diff} ثانية

*⚠️ تحذير: تم اكتشاف محاولة استخدام نفس الحساب من جهاز مختلف خلال أقل من 60 ثانية*
"""
    
    # Send to each admin
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=alert_message,
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Failed to send alert to admin {admin_id}: {e}")