import os
import time
import requests
import pandas as pd
from ta.momentum import RSIIndicator
from flask import Flask, request

# --- Environment variables ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# --- Flask app setup ---
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Coinbase Signal Bot is running successfully!"

# --- Telegram send function ---
def send_signal(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"❌ Error sending message: {e}")

# --- Get Coinbase candles ---
def get_coin_data(symbol="BTC-USD"):
    try:
        url = f"https://api.exchange.coinbase.com/products/{symbol}/candles?granularity=3600"
        response = requests.get(url)
        if response.status_code != 200:
            return None
        data = response.json()
        df = pd.DataFrame(data, columns=["time", "low", "high", "open", "close", "volume"])
        df = df.sort_values("time")
        return df
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

# --- Analyze RSI signal ---
def analyze_signal(df):
    rsi = RSIIndicator(df["close"], window=14).rsi().iloc[-1]
    if rsi < 30:
        return "🟢 <b>BUY Signal</b> (RSI < 30)"
    elif rsi > 70:
        return "🔴 <b>SELL Signal</b> (RSI > 70)"
    else:
        return None

# --- Top 20 Coinbase symbols ---
TOP20 = [
    "BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD", "XRP-USD",
    "AVAX-USD", "DOGE-USD", "LTC-USD", "DOT-USD", "LINK-USD",
    "MATIC-USD", "BCH-USD", "ATOM-USD", "UNI-USD", "FIL-USD",
    "NEAR-USD", "AAVE-USD", "SAND-USD", "ICP-USD", "EGLD-USD"
]

# --- Main signal loop ---
def run_signals():
    send_signal("🤖 <b>Top20 Coinbase Signal Bot started!</b>\nChecking every 30 minutes...")
    while True:
        messages = []
        for coin in TOP20:
            df = get_coin_data(coin)
            if df is None or len(df) < 15:
                continue
            signal = analyze_signal(df)
            if signal:
                messages.append(f"{coin}: {signal}")
        if messages:
            send_signal("\n".join(messages))
        else:
            send_signal("⚪ No strong signals detected this cycle.")
        time.sleep(1800)  # 30 minutes

# --- Webhook route ---
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        update = request.get_json()
        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            text = update["message"]["text"]

            if text == "/start":
                send_signal("👋 Բարի գալուստ Top20 Coinbase Signal Bot!\nՍիգնալները կստանաս ամեն 30 րոպեն մեկ 📈")
        return {"ok": True}

# --- Run Flask and bot ---
if __name__ == "__main__":
    import threading
    t = threading.Thread(target=run_signals)
    t.daemon = True
    t.start()
    app.run(host="0.0.0.0", port=10000)
