import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# === Environment Variables ===
TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# === Flask App ===
app = Flask(__name__)

# === Logging ===
logging.basicConfig(level=logging.INFO)

# === Telegram Bot Setup ===
application = Application.builder().token(TOKEN).build()

# ===== BOT COMMANDS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Բարի գալուստ Coinbase AI Bot-ին!\nՍտուգում եմ շուկան...")

application.add_handler(CommandHandler("start", start))

# ===== FLASK ROUTES =====
@app.route("/")
def home():
    return "✅ Coinbase AI Bot is running successfully!"

@app.route("/webhook", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "ok"

# ===== STARTUP =====
async def main():
    await application.bot.delete_webhook()
    await application.bot.set_webhook(f"{WEBHOOK_URL}/webhook")
    logging.info(f"🚀 Webhook set to {WEBHOOK_URL}/webhook")
    app.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    asyncio.run(main())

