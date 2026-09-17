import os
import asyncio
import logging
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
import yt_dlp

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")  # توکن از environment variable خونده می‌شه
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! لینک پست یا ریلز اینستاگرام رو برام بفرست تا دانلودش کنم."
    )


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if "instagram.com" not in url:
        await update.message.reply_text("لطفاً یک لینک معتبر اینستاگرام بفرست.")
        return

    status_msg = await update.message.reply_text("در حال دانلود... ⏳")

    ydl_opts = {
        "outtmpl": os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s"),
        "quiet": True,
        "noplaylist": True,
        # ترجیح دادن یک فایل ترکیب‌شده‌ی آماده به جای دانلود جداگانه‌ی صدا و تصویر
        "format": "best[ext=mp4]/best",
        "socket_timeout": 30,
        "retries": 5,
        "fragment_retries": 5,
        # اگه لوکال روی ایران اجرا می‌کنی و پروکسی پایدار داری، این خط رو باز کن:
        # "proxy": "socks5://127.0.0.1:1080",  # یا آدرس پروکسی خودت
    }

    filename = None
    try:
        # چون yt-dlp یک عملیات "blocking" ئه، تو یک thread جدا اجراش می‌کنیم
        # تا حلقه‌ی اصلی ربات (event loop) قفل نشه و ربات فریز نکنه
        def run_download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)

        filename = await asyncio.to_thread(run_download)

        if filename.lower().endswith((".mp4", ".mov", ".mkv", ".webm")):
            with open(filename, "rb") as f:
                await update.message.reply_video(video=f)
        else:
            with open(filename, "rb") as f:
                await update.message.reply_photo(photo=f)

        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"خطا در دانلود:\n{e}")

    finally:
        # پاک کردن فایل موقت بعد از ارسال
        if filename and os.path.exists(filename):
            os.remove(filename)


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    print("ربات در حال اجراست...")
    app.run_polling()


# ---------- بخش keep-alive برای Replit ----------
# یک وب‌سرور خیلی ساده که UptimeRobot بهش پینگ می‌زنه
# تا Replit فکر کنه ترافیک داره و ربات رو نخوابونه
web = Flask(__name__)


@web.route("/")
def home():
    return "ربات فعاله ✅"


def run_web():
    web.run(host="0.0.0.0", port=8080)


def keep_alive():
    t = threading.Thread(target=run_web)
    t.start()
# -------------------------------------------------


if __name__ == "__main__":
    keep_alive()
    main()
