import telebot
import requests
import time

BOT_TOKEN = "ՔՈ_TOKENԸ_ԴԻՐ_ԱՅՍՏԵՂ"
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
        response = requests.get(url)
        data = response.json()
        price = float(data["data"]["amount"])

        # Պարզ օրինակ՝ ցույց տալու համար
        rsi = (price % 100) / 100  
        macd = (price * 1.1) % 100 / 100
        ema = (price * 0.9) % 100 / 100

        confidence = ((rsi + macd + ema) / 3) * 100 - 50

        if confidence >= 75:
            signal_type = "🟢 Strong BUY"
        elif confidence >= 50:
            signal_type = "🟡 Medium BUY"
        elif confidence >= 30:
            signal_type = "🟠 Weak BUY"
        elif confidence <= -75:
            signal_type = "🔴 Strong SELL"
        elif confidence <= -50:
            signal_type = "🟣 Medium SELL"
        elif confidence <= -30:
            signal_type = "⚫ Weak SELL"
        else:
            signal_type = None

        if signal_type:
            bot.send_message(
                CHAT_ID,
                f"💎 *{coin}* Signal Detected!\n\n"
                f"📈 Type: {signal_type}\n"
                f"💰 Confidence: {abs(confidence):.1f}%\n"
                f"💵 Current Price: ${price:.2f}",
                parse_mode="Markdown"
            )
            return True
        return False

    except Exception as e:
        print(f"Error fetching {coin}: {e}")
        return False

def main():
    bot.send_message(CHAT_ID, "🤖 Top20 Coinbase Signal Bot started!\nChecking every 10 minutes...")
    while True:
        any_signal = False
        for coin in COINS:
            if get_signal(coin):
                any_signal = True
            time.sleep(2)

        if not any_signal:
            bot.send_message(CHAT_ID, "⚪ No strong signals detected this cycle.")
        bot.send_message(CHAT_ID, "✅ Cycle complete. Next check in 10 minutes ⏱️")
        time.sleep(600)

if __name__ == "__main__":
    main()

