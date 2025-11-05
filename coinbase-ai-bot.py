import requests, time, pandas as pd, threading, asyncio, random
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

# ======== ⚙️ Քո կարգավորումները ========
TELEGRAM_TOKEN = "TELEGRAM_TOKEN"
CHAT_ID = "CHAT_ID"
OPENAI_API_KEY = "OPENAI_API_KEY"
client = OpenAI(api_key=OPENAI_API_KEY)

bot = Bot(token=TELEGRAM_TOKEN)

COINS = [
    "BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD", "AVAX-USD",
    "LTC-USD", "MATIC-USD", "BCH-USD", "DOGE-USD"
]

INTERVAL = 3600  # 🕐 1 ժամ

# ======== 📈 Տվյալների ստացում ========
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

    # 💡 Trend filter
    if ema20 > ema50 and rsi < 40 and close > ema20 and prev["close"] < prev["ema20"]:
        direction = "BUY"
    elif ema20 < ema50 and rsi > 60 and close < ema20 and prev["close"] > prev["ema20"]:
        direction = "SELL"
    else:
        return None, rsi

    # 🎯 Profit / Stop-loss առաջարկներ
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

# ======== 🧠 AI գնահատում ========
async def ai_analyze_signal(signal_text: str) -> str:
    prompt = f"Դու փորձառու crypto trader ես։ Վերլուծիր այս սիգնալը և գնահատիր վստահությունը՝ բարձր, միջին կամ ցածր։ Պատասխանիր հայերեն.\n\n{signal_text}"
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# ======== 🤖 Բոտի հրամաններ ========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Բարի գալուստ **Smart Crypto Bot**-ին!\n\n"
        "📊 Ես ստուգում եմ շուկան ամեն ժամ մեկ և ուղարկում եմ միայն վստահելի BUY/SELL սիգնալներ՝ profit/stop-loss-ով։\n"
        "💬 Կարող ես ինձ գրել ցանկացած crypto հարց։"
    )

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    prompt = f"Crypto expert AI, answer in Armenian: {user_message}"
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    answer = response.choices[0].message.content.strip()
    await update.message.reply_text(answer)

# ======== 🚀 Սիգնալների ֆունկցիա ========
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
        time.sleep(3600)  # 1 ժամ

async def send_ai_signal(signal_text):
    ai_eval = await ai_analyze_signal(signal_text)
    final_msg = f"{signal_text}\n\n🤖 AI գնահատում՝ {ai_eval}"
    bot.send_message(chat_id=CHAT_ID, text=final_msg, parse_mode="Markdown")

# ======== 🏁 Գործարկում ========
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    threading.Thread(target=signal_loop, daemon=True).start()
    print("✅ Bot started.")
    app.run_polling()

if __name__ == "__main__":
    main()
