from concurrent.futures import ThreadPoolExecutor, as_completed
import telebot
import requests
import time
import random

BOT_TOKEN = "ՔՈ_TOKENԸ"
CHAT_ID = "ՔՈ_CHAT_ID_Ը"
bot = telebot.TeleBot(BOT_TOKEN)

COINS = [
    "BTC-USD", "ETH-USD", "ADA-USD", "SOL-USD", "XRP-USD", "AVAX-USD", "DOGE-USD",
    "DOT-USD", "MATIC-USD", "LTC-USD", "BCH-USD", "LINK-USD", "ATOM-USD",
    "AAVE-USD", "FIL-USD", "ICP-USD", "UNI-USD", "ETC-USD", "NEAR-USD", "APT-USD"
]

def get_signal(coin):
    try:
        url = f"https://api.coinbase.com/v2/prices/{coin}/spot"
        response = requests.get(url, timeout=5)
        price = float(response.json()["data"]["amount"])

        # Պարզ confidence հաշվարկ
        conf = ((price % 100) / 100 - 0.5) * 200  # [-100, +100]

        if conf >= 75:
            signal = "🟢 Strong BUY"
        elif conf >= 50:
            signal = "🟡 Medium BUY"
        elif conf >= 30:
            signal = "🟠 Weak BUY"
        elif conf <= -75:
            signal = "🔴 Strong SELL"
        elif conf <= -50:
            signal = "🟣 Medium SELL"
        elif conf <= -30:
            signal = "⚫ Weak SELL"
        else:
            return None

        # Stop Loss / Take Profit
        sl_p = 0.03 + random.uniform(0.01, 0.02)
        tp_p = 0.06 + random.uniform(0.02, 0.03)

        sl = price * (1 - sl_p) if "BUY" in signal else price * (1 + sl_p)
        tp = price * (1 + tp_p) if "BUY" in signal else price * (1 - tp_p)

        msg = (
            f"📊 *{coin} Signal!*\n"
            f"💡 Type: {signal}\n"
            f"🤖 Confidence: {abs(conf):.1f}%\n"
            f"💰 Price: ${price:.2f}\n"
            f"🎯 TP: ${tp:.2f}\n"
            f"🛑 SL: ${sl:.2f}\n"
            f"⏰ Timeframe: 30m"
        )
        return msg
    except:
        return None

def check_all():
    signals = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(get_signal, coin): coin for coin in COINS}
        for future in as_completed(futures):
            result = future.result()
            if result:
                signals.append(result)

    if signals:
        for msg in signals:
            bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
            time.sleep(1)
    else:
        bot.send_message(CHAT_ID, "⚪ No strong signals detected this cycle.")

def main():
    bot.send_message(CHAT_ID, "🤖 Top20 Coinbase Signal Bot started with ThreadPool!\nChecking every 10 minutes...")
    while True:
        check_all()
        bot.send_message(CHAT_ID, "✅ Cycle complete. Next check in 10 minutes ⏱️")
        time.sleep(600)

if __name__ == "__main__":
    main()

