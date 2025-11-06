import os
import time
import threading
import requests
import pandas as pd
import numpy as np
from flask import Flask, request
import telebot
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, MACD

# === CONFIG ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
bot = telebot.TeleBot(TELEGRAM_TOKEN)

app = Flask(__name__)

COINS = [
    "BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD", "XRP-USD", "DOGE-USD",
    "AVAX-USD", "LTC-USD", "LINK-USD", "MATIC-USD", "BCH-USD", "NEAR-USD",
    "UNI-USD", "ATOM-USD", "APT-USD", "ICP-USD", "ARB-USD", "FIL-USD",
    "PEPE-USD", "SHIB-USD"
]

# === FUNCTIONS ===
def get_data(symbol, limit=100):
    url = f"https://api.exchange.coinbase.com/products/{symbol}/candles?granularity=1800"
    resp = requests.get(url)
    data = resp.json()
    if not isinstance(data, list):
        return None
    df = pd.DataFrame(data, columns=['time','low','high','open','close','volume'])
    df = df.sort_values(by='time')
    return df

def analyze(symbol):
    df = get_data(symbol)
    if df is None or len(df) < 50:
        return None

    close = df['close']
    volume = df['volume']

    rsi = RSIIndicator(close).rsi()
    ema20 = EMAIndicator(close, 20).ema_indicator()
    ema50 = EMAIndicator(close, 50).ema_indicator()
    macd = MACD(close).macd()

    signals = []
    confidence = 0

    # RSI
    if rsi.iloc[-1] < 30:
        signals.append("RSI<30 (BUY)")
        confidence += 25
    elif rsi.iloc[-1] > 70:
        signals.append("RSI>70 (SELL)")
        confidence -= 25

    # MACD
    if macd.iloc[-1] > macd.iloc[-2]:
        signals.append("MACD rising (BUY)")
        confidence += 25
    elif macd.iloc[-1] < macd.iloc[-2]:
        signals.append("MACD falling (SELL)")
        confidence -= 25

    # EMA Trend
    if ema20.iloc[-1] > ema50.iloc[-1]:
        signals.append("EMA20>EMA50 (BUY)")
        confidence += 25
    elif ema20.iloc[-1] < ema50.iloc[-1]:
        signals.append("EMA20<EMA50 (SELL)")
        confidence -= 25

    # Volume
    if volume.iloc[-1] > volume.mean() * 1.1:
        signals.append("High Volume")
        confidence += 25

    # 10%-ից սկսած ուղարկենք
    signal_type = "BUY" if confidence >= 10 else "SELL" if confidence <= -10 else None
    if not signal_type:
        return None

    price = close.iloc[-1]
    volatility = (df['high'] - df['low']).mean() / price

    take_profit = price * (1 + volatility * 1.5) if signal_type == "BUY" else price * (1 - volatility * 1.5)
    stop_loss = price * (1 - volatility * 0.8) if signal_type == "BUY" else price * (1 + volatility * 0.8)

    # Գույն ըստ վստահության
    if abs(confidence) >= 70:
        emoji = "🟢"
    elif abs(confidence) >= 40:
        emoji = "🟡"
    else:
        emoji = "🔴"

    return {
        "symbol": symbol,
        "type": signal_type,
        "confidence": abs(confidence),
        "price": price,
        "tp": take_profit,
        "sl": stop_loss,
        "signals": signals,
        "emoji": emoji
    }

def check_all():
    print("🔄 Checking signals...")
    found = False
    for coin in COINS:
        result = analyze(coin)
        if result:
            found = True
            msg = f"""
{result['emoji']} *{result['symbol']} Signal!*
💡 Type: *{result['type']}*
📊 Confidence: *{result['confidence']}%*
💰 Price: {result['price']:.2f}$
🎯 Take Profit: {result['tp']:.2f}$
🛑 Stop Loss: {result['sl']:.2f}$
📈 Indicators:
{chr(10).join(['- ' + s for s in result['signals']])}
⏰ 30m timeframe
"""
            try:
                bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                time.sleep(1)
            except Exception as e:
                print(f"⚠️ Telegram send error: {e}")
                time.sleep(2)
    if not found:
        bot.send_message(CHAT_ID, "⚪ No signals this cycle.")
    else:
        bot.send_message(CHAT_ID, "✅ Cycle complete. Next check in 3 minutes ⏱️")

def loop_signals():
    while True:
        check_all()
        time.sleep(180)  # 3 րոպե

@app.route('/')
def home():
    return "Bot is running ✅"

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_data().decode("utf-8")
    bot.process_new_updates([telebot.types.Update.de_json(update)])
    return "OK", 200

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🤖 Bot started! Checking every 3 minutes, signals from 10%+")

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url="https://coinbase-ai-bot.onrender.com/webhook")
    print("✅ Bot running...")
    threading.Thread(target=loop_signals, daemon=True).start()
    app.run(host="0.0.0.0", port=10000)
