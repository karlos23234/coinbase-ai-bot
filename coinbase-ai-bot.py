import os
import asyncio
import requests
import pandas as pd
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from openai import OpenAI
from aiohttp import web

# Env
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

COINS = ["BTC-USD","ETH-USD","SOL-USD","ADA-USD","XRP-USD","AVAX-USD","DOGE-USD","LTC-USD","BCH-USD","LINK-USD",
         "UNI-USD","MATIC-USD","ETC-USD","DOT-USD","FIL-USD","ATOM-USD","NEAR-USD","AAVE-USD","SAND-USD","ICP-USD"]

SIGNAL_CHECK_INTERVAL = 1800  # 30 min

client = OpenAI(api_key=OPENAI_KEY)

# Coinbase signal check
def get_coin_signal(coin):
    url = f"https://api.exchange.coinbase.com/products/{coin}/candles?granularity=3600"
    data = requests.get(url).json()
    df = pd.DataFrame(data, columns=["time","low","high","open","close","volume"])
    df = df.sort_values("time")
    df["rsi"] = RSIIndicator(df["close"]).rsi()
    df["ema"] = EMAIndicator(df["close"], window=20).ema_indicator()
    last = df.iloc[-1]
    signal = "BUY ✅" if last["rsi"] < 30 and last["close"] > last["ema"] else \
             "SELL ⚠️" if last["rsi"] > 70 and last["close"] < last["ema"] else "HOLD ⏸"
    return coin, signal

# AI evaluation
def ai_comment(coin, signal):
    prompt = f"{coin} currently has a {signal} signal based on RSI/EMA. Give short trading insight."
    ans = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}])
    return ans.choices[0].message.content.strip()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Բարի գալուստ Top20 Coinbase Signal Bot!")

async def check_signals(context: ContextTypes.DEFAULT_TYPE):
    texts = []
    for coin in COINS:
        c, s = get_coin_signal(coin)
        texts.append(f"{c}: {s}")
    msg = "\n".join(texts)
    await context.bot.send_message(chat_id=CHAT_ID, text=f"📊 Թարմացված սիգնալներ:\n{msg}")

# Flask → aiohttp webhook
async def handle(request):
    data = await request.json()
    update = Update.de_json(data, context.application.bot)
    await context.application.process_update(update)
    return web.Response(text="ok")

async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    job = app.job_queue.run_repeating(check_signals, interval=SIGNAL_CHECK_INTERVAL, first=10)

    await app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")

    aio_app = web.Application()
    aio_app.router.add_post("/webhook", lambda r: handle(r))
    runner = web.AppRunner(aio_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()

    print("🚀 Bot running...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())

