import os
import requests, time, pandas as pd, threading, asyncio, random
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
from flask import Flask, request

# ======== ⚙️ Կարգավորումներ ========
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID", "YOUR_CHAT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://YOUR_RENDER_URL.onrender.com")

client = OpenAI(api_key=OPENAI_API_KEY)
bot = Bot(token=TELEGRAM_TOKEN)

app = Flask(__name__)

COINS = [
    "BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD", "AVAX-USD",
    "LTC-USD", "MATIC-USD", "BCH-USD", "DOGE-USD"
]

INTERVAL = 3600  # 1 ժամ

# ======== 📈 Գների տվյալներ ========
def get_prices(symbol, granularity=INTERVAL):
    url = f"https://api.exchange.coinbase.com/products/{symbol}/candles?granularity={granularity}"
    resp = requests.get(url)
    data = resp.json()
    if not isinstance(data, list):
        return None
    df = pd.DataFrame(data, columns=["time","low","high","open","close","volume"])
    df = df.sort_values("time")
    df["close"] = df["close"].astype(float)
    return df

# ======== 💹 Սիգնալի ստուգում ========
def get_signal(symbol):
    df = get_prices(symbol)
    if df is None or len(df) < 50:
        return None, None
    df["rsi"] = RSIIndicator(df["close"], window=14).rsi()
    df["ema20"] = EMAIndicator(df["close"], window=20).ema_indicator()
    df["ema50"] = EMAIndicator(df["close"], window=50).ema_indicator()

    last = df.iloc[-1]
    prev = df.iloc[-2]
    rsi, close, ema20, ema50 = last["rsi"], last["close"], last["ema20"], last["ema50"]

    if ema20 > ema50 and rsi < 40 and close > ema20 and prev["close"] < prev["ema20"]:
        direction = "BUY"
    elif ema20 < ema50 and rsi > 60 and close < ema20 and prev["close"] > prev["ema20"]:
        direction = "SELL"
    else:
        return None, rsi

    if direction == "BUY":
        profit = round(close * (1 + random.uniform(0.025, 0.04)), 4)
        stop = round(close * (1 - random.uniform(0.012, 0.02)), 4)
    else:
        profit = round(close * (1 - random.uniform(0.025, 0.04)), 4)
        stop = round(close * (1 + random.uniform(0.012, 0.02)), 4)

    signal_text = (
        f"💹 **{direction} SIGNAL** for {symbol}\n"
        f"RSI: {rsi:.1f}\n"
        f"Trend: {'Up ✅' if ema20 > ema50 else 'Down ⚠️'}\n\n"
        f"🎯 Profit Target: {profit}\n"
        f"🛑 Stop Loss: {stop}"
    )

    return signal_text, rsi

# ======== 🤖 AI գնահատում ========
async def ai_analyze_signal(signal_text: str) -> str:
    prompt = f"Դու փորձառու crypto trader ես։ Վերլուծիր այս սիգնալը և գնահատիր վստահությունը՝ բարձր, միջին կամ ցածր։ Պատասխանիր հայերեն.\n\n{signal_text}"
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# ======== Telegram Bot ========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Բարի գալուստ **Coinbase AI Bot**-ին!\nՍտուգում եմ շուկան և ուղարկում վստահելի սիգնալներ։")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    prompt = f"Crypto expert AI, answer in Armenian: {user_message}"
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    await update.message.reply_text(response.choices[0].message.content.strip())

def signal_loop():
    while True:
        print("🔄 Ստուգում է շուկան...")
        for coin in COINS:
            try:
                sig, rsi = get_signal(coin)
                if sig:
                    asyncio.run(send_ai_signal(sig))
                time.sleep(2)
            except Exception as e:
                print("❌", e)
        time.sleep(3600)

async def send_ai_signal(signal_text):
    ai_eval = await ai_analyze_signal(signal_text)
    final_msg = f"{signal_text}\n\n🤖 AI գնահատում՝ {ai_eval}"
    bot.send_message(chat_id=CHAT_ID, text=final_msg, parse_mode="Markdown")

# ======== Flask webhook ========
@app.route("/")
def home():
    return "✅ Coinbase AI Bot is running with webhook!", 200

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def receive_update():
    update = Update.de_json(request.get_json(force=True), bot)
    asyncio.run(app_instance.process_update(update))
    return "ok", 200

def run_webhook():
    bot.delete_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}")
    threading.Thread(target=signal_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))

# ======== Start ========
if __name__ == "__main__":
    app_instance = Application.builder().token(TELEGRAM_TOKEN).build()
    app_instance.add_handler(CommandHandler("start", start))
    app_instance.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    print("🚀 Starting Coinbase AI Bot with Webhook...")
    run_webhook()
