import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Env variables
TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Flask app
app = Flask(__name__)

# Telegram Application
application = Application.builder().token(TOKEN).build()


# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Բոտը աշխատում է հաջողությամբ Render-ի վրա։")


application.add_handler(CommandHandler("start", start))


# --- Flask webhook route ---
@app.route("/webhook", methods=["POST"])
async def webhook():
    if request.method == "POST":
        update_data = request.get_json(force=True)
        update = Update.de_json(update_data, application.bot)
        # 🔹 Initialize application if not yet done
        if not application.running:
            await application.initialize()
        await application.process_update(update)
        return "ok", 200


@app.route("/", methods=["GET"])
def home():
    return "🚀 Coinbase AI Bot is running on Render", 200


# --- Main ---
if __name__ == "__main__":
    import asyncio
    async def main():
        # Remove old webhook if any
        await application.bot.delete_webhook()
        # Set new webhook
        await application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
        logger.info(f"🚀 Webhook set to {WEBHOOK_URL}/webhook")
        # Run Flask
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

    asyncio.run(main())
