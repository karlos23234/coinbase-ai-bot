# coinbase_ai_bot.py
import os
import time
import threading
import random
import requests
import pandas as pd
import asyncio
from flask import Flask, request
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

# ===== ⚙️ Settings =====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TELEGRAM_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID", "YOUR_CHAT_ID"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://your-app.onrender.com")

client = OpenAI(api_key=OPENAI_API_KEY)

COINS = [
    "BTC-USD","ETH-USD","USDT-USD","SOL-USD","ADA-USD","XRP-USD","DOGE-USD","AVAX-USD",
    "LTC-USD","LINK-USD","MATIC-USD","DOT-USD","BCH-USD","ATOM-USD","NEAR-USD","TRX-USD",
    "ICP-USD","APT-USD","XTZ-USD","XLM-USD"
]

SIGNAL_CHECK_INTERVAL = 30
CANDLE_GRANULARITY = 60
MIN_CANDLES = 50

app = Flask(__name__)
app_instance = None

# ===== 📈 Data =====
def get_prices(symbol, granularity=CANDLE_GRANULARITY):
    url = f"https://api.exchange.coinbase.com/products/{symbol}/candles?granularity={granularity}"
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
        if not isinstance(data, list):
            return None
        df = pd.DataFrame(data, columns=["time","low","high","open","close","volume"])
        df = df.sort_values("time")
        df["close"] = df["close"].astype(float)
        return df
    except Exception as e:
        print("get_prices error:", e)
        return None

def get_signal(symbol):
    df = get_prices(symbol)
    if df is None or len(df) < MIN_CANDLES:
        return None, None
    try:
        df["rsi"] = RSIIndicator(df["close"], window=14).rsi()
        df["ema20"] = EMAIndicator(df["close"], window=20).ema_indicator()
        df["ema50"] = EMAIndicator(df["close"], window=50).ema_indicator()
        last = df.iloc[-1]
        prev = df.iloc[-2]
        rsi, close, ema20, ema50 = last["rsi"], last["close"], last["ema20"], last["ema50"]

        direction = None
        if ema20 > ema50 and rsi < 40 and close > ema20 and prev["close"] < prev["ema20"]:
            direction = "BUY"
        elif ema20 < ema50 and rsi > 60 and close < ema20 and prev["close"] > prev["ema20"]:
            direction = "SELL"
        else:
            return None, rsi

        if direction == "BUY":
            profit = round(close * (1 + random.uniform(0.02, 0.05)), 4)
            stop = round(close * (1 - random.uniform(0.01, 0.03)), 4)
        else:
            profit = round(close * (1 - random.uniform(0.02, 0.05)), 4)
            stop = round(close * (1 + random.uniform(0.01, 0.03)), 4)

        signal_text = (
            f"💹 *{direction} SIGNAL* — `{symbol}`\n"
            f"Price: `{close}`\n"
            f"RSI: `{rsi:.1f}`\n"
            f"Trend: {'Up ✅' if ema20 > ema50 else 'Down ⚠️'}\n"
            f"🎯 Profit target: `{profit}`\n"
            f"🛑 Stop loss: `{stop}`"
        )
        return signal_text, rsi
    except Exception as e:
        print("get_signal error:", e)
        return None, None

# ===== 🤖 AI =====
async def ai_analyze_signal(signal_text: str) -> str:
    try:
        prompt = (
            "Դու փորձառու crypto trader ես։ Կարճ ձևով գնահատիր այս սիգնալի վստահությունը՝ Բարձր, Միջին կամ Ցածր։ "
            "Նշիր նաև մեկ կարճ պատճառ։ Պատասխանիր հայերեն.\n\n"
            f"{signal_text}"
        )
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=60,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("AI analyze error:", e)
        return "AI գնահատումը անհասանելի է։"

# ===== Telegram =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Բարի գալուստ Top20 Coinbase Signal Bot!")

async def manual_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texts = []
    for coin in COINS[:10]:
        df = get_prices(coin)
        if df is None:
            texts.append(f"{coin}: ❌ տվյալ չկա")
        else:
            price = df.iloc[-1]["close"]
            texts.append(f"{coin}: {price}")
    await update.message.reply_text("📊 Գները՝\n" + "\n".join(texts))

async def send_ai_signal_async(signal_text: str):
    ai_eval = await ai_analyze_signal(signal_text)
    final_msg = f"{signal_text}\n\n🤖 AI գնահատում՝ {ai_eval}"
    await app_instance.bot.send_message(chat_id=CHAT_ID, text=final_msg, parse_mode="Markdown")

def send_ai_signal(signal_text: str):
    asyncio.run(send_ai_signal_async(signal_text))

def signal_loop():
    print("🔁 Սկսում է ստուգումը...")
    while True:
        for coin in COINS:
            try:
                sig, rsi = get_signal(coin)
                if sig:
                    print("Signal found:", coin)
                    send_ai_signal(sig)
                time.sleep(1)
            except Exception as e:
                print("Loop error:", e)
        time.sleep(SIGNAL_CHECK_INTERVAL)

# ===== Flask webhook =====
@app.route("/", methods=["GET"])
def home():
    return "✅ Coinbase Top20 Bot աշխատում է", 200

@app.route("/webhook", methods=["POST"])
def receive_update():
    if not app_instance:
        return "app not ready", 500
    update = Update.de_json(request.get_json(force=True), app_instance.bot)
    asyncio.run(app_instance.process_update(update))
    return "ok", 200

# ===== Main =====
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app_instance = Application.builder().token(TELEGRAM_TOKEN).build()
    app_instance.add_handler(CommandHandler("start", start))
    app_instance.add_handler(CommandHandler("signal", manual_signal))
    app_instance.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manual_signal))

    async def init_and_start():
        await app_instance.initialize()
        await app_instance.bot.delete_webhook()
        await app_instance.bot.set_webhook(f"{WEBHOOK_URL}/webhook")
        print("🚀 Webhook set")

    loop.run_until_complete(init_and_start())
    threading.Thread(target=signal_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))

