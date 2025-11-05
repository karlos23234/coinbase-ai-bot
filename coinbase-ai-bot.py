import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Telegram bot token
TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Flask app
app = Flask(__name__)

# Logging
logging.basicConfig(level=logging.INFO)

# Create async Telegram Application
application = Application.builder().token(TOKEN).build()


# ====== BOT COMMANDS ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Բարի գալուստ Coinbase AI Bot-ին!\nՍտուգում եմ շուկան...")


# Register command
application.add_handler(CommandHandler("start", start))


# ====== FLASK ROUTES ======
@app.route("/")
def home():
    return "Coinbase AI Bot is running ✅"


@app.route("/webhook", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "ok"


# ====== STARTUP ======
async def run():
    # Remove old webhook (եթե կա)
    await application.bot.delete_webhook()
    # Set new webhook
    await application.bot.set_webhook(f"{WEBHOOK_URL}/webhook")
    logging.info(f"🚀 Webhook set to {WEBHOOK_URL}/webhook")

    # Start Flask server
    app.run(host="0.0.0.0", port=10000)


if __name__ == "__main__":
    asyncio.run(run())

