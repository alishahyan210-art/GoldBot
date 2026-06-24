import os
import json
import asyncio
import logging
import urllib.request
from datetime import datetime
from groq import Groq
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, JobQueue
import pytz

# ─────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8651506670:AAFkwznXEQl_Yg9Lowiy6kVffrPtaM8mW_w")
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY",   "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")
YOUR_CHAT_ID   = int(os.environ.get("YOUR_CHAT_ID", "7028226344"))

PAKISTAN_TZ = pytz.timezone("Asia/Karachi")

# ─────────────────────────────────────────
#  USER LANGUAGE SETTINGS
# ─────────────────────────────────────────
user_language = {}

def get_lang(chat_id):
    return user_language.get(chat_id, "english")

# ─────────────────────────────────────────
#  REAL-TIME PRICES — YAHOO FINANCE
# ─────────────────────────────────────────
def get_live_prices():
    symbols = {
        "gold":  "GC=F",
        "silver":"SI=F",
        "dxy":   "DX-Y.NYB",
        "oil":   "CL=F",
        "eurusd":"EURUSD=X",
        "gbpusd":"GBPUSD=X",
    }
    prices = {}
    for name, symbol in symbols.items():
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read())
            result = data["chart"]["result"][0]
            meta   = result["meta"]
            current = meta.get("regularMarketPrice", 0)
            prev    = meta.get("chartPreviousClose", current)
            change  = ((current - prev) / prev * 100) if prev else 0
            prices[name] = {"price": current, "change": round(change, 2)}
        except Exception:
            prices[name] = {"price": 0, "change": 0}
    return prices

def format_prices(prices):
    def fmt(name, symbol, decimals=2):
        p = prices.get(name, {})
        price  = p.get("price", 0)
        change = p.get("change", 0)
        arrow  = "▲" if change >= 0 else "▼"
        sign   = "+" if change >= 0 else ""
        return f"{symbol}: ${price:,.{decimals}f}  {arrow} {sign}{change}%"

    return (
        f"{fmt('gold',  'Gold  XAU/USD', 2)}\n"
        f"{fmt('silver','Silver XAG/USD', 2)}\n"
        f"{fmt('dxy',   'DXY           ', 2)}\n"
        f"{fmt('oil',   'Oil  WTI      ', 2)}\n"
        f"{fmt('eurusd','EUR/USD       ', 4)}\n"
        f"{fmt('gbpusd','GBP/USD       ', 4)}"
    )

# ─────────────────────────────────────────
#  GROQ AI CALL
# ─────────────────────────────────────────
def ask_groq(prompt: str) -> str:
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()

# ─────────────────────────────────────────
#  GOLD BRIEF GENERATOR
# ─────────────────────────────────────────
def generate_gold_brief(language: str, prices: dict) -> str:
    today = datetime.now(PAKISTAN_TZ).strftime("%A, %d %B %Y")
    gold_price  = prices.get("gold",  {}).get("price",  0)
    gold_change = prices.get("gold",  {}).get("change", 0)
    dxy_change  = prices.get("dxy",   {}).get("change", 0)
    oil_price   = prices.get("oil",   {}).get("price",  0)
    dxy_dir     = "Upar ja raha hai" if dxy_change > 0 else "Neeche aa raha hai"
    dxy_dir_en  = "Rising" if dxy_change > 0 else "Falling"

    if language == "urdu":
        prompt = f"""Tu ek professional Gold market analyst hai. Aaj ki date hai {today}.

REAL-TIME DATA (abhi ka):
- Gold price: ${gold_price:,.2f} ({gold_change:+.2f}% aaj)
- DXY: {dxy_dir} ({dxy_change:+.2f}%)
- Oil: ${oil_price:,.2f}

Yeh REAL prices use karke Gold ka hafta wari analysis do Roman Urdu mein.

Include karo:
- Fed stance, Real yields, Geopolitical risk, CFTC positioning
- Bias verdict BEARISH/BULLISH/NEUTRAL
- Score 0-100
- 4-5 short reasons WHY
- Factor signals
- Support/Resistance levels
- Is hafte ke key events

Format bilkul aisa (Telegram ke liye):

📊 GOLD HAFTA WARI BRIEF — {today}
━━━━━━━━━━━━━━━━━━━━━

📍 Qeemat: ${gold_price:,.2f} | Aaj: {gold_change:+.2f}%
📊 Rukh: [VERDICT] | Score: [X]/100
💡 Asli wajah: [one line]

KYUN [VERDICT]:
→ [wajah 1 - simple Urdu]
→ [wajah 2]
→ [wajah 3]
→ [wajah 4]
→ [wajah 5]

━━━━━━━━━━━━━━━━━━━━━
FACTOR CHECK:
🔴/🟡/🟢 Fed       → [Urdu mein]
🔴/🟡/🟢 Dollar    → {dxy_dir} ({dxy_change:+.2f}%)
🔴/🟡/🟢 Yields    → [Urdu mein]
🔴/🟡/🟢 Geo Risk  → [Urdu mein]
🔴/🟡/🟢 Tel       → ${oil_price:,.2f}
🔴/🟡/🟢 CFTC      → [Urdu mein]

━━━━━━━━━━━━━━━━━━━━━
CFTC DATA (Latest):
Spec longs:  [number]
Spec shorts: [number]
Net:         [number] [direction]
Signal: [plain Urdu mein]

━━━━━━━━━━━━━━━━━━━━━
KEY LEVELS:
Support:    $[level] (yahan se bounce ho sakta)
Resistance: $[level] (yahan tak resistance)

IS HAFTE WATCH KARO:
⚠️ [Date] — [Event] [impact]
   Agar zyada → Gold [prediction]
   Agar kam   → Gold [prediction]

━━━━━━━━━━━━━━━━━━━━━
JPM saal ke aakhir target: $6,000/oz 🎯"""

    else:
        prompt = f"""You are a professional Gold market analyst. Today is {today}.

REAL-TIME DATA (live):
- Gold price: ${gold_price:,.2f} ({gold_change:+.2f}% today)
- DXY: {dxy_dir_en} ({dxy_change:+.2f}%)
- Oil: ${oil_price:,.2f}

Use these REAL prices and give a weekly Gold analysis for a beginner trader.

Include: Fed stance, Real yields, Geopolitical risk, CFTC positioning.

Format exactly like this:

📊 GOLD WEEKLY BRIEF — {today}
━━━━━━━━━━━━━━━━━━━━━

📍 Spot: ${gold_price:,.2f} | Today: {gold_change:+.2f}%
📊 Bias: [VERDICT] | Score: [X]/100
💡 Main driver: [one line]

WHY [VERDICT]:
→ [reason 1]
→ [reason 2]
→ [reason 3]
→ [reason 4]
→ [reason 5]

━━━━━━━━━━━━━━━━━━━━━
FACTOR BREAKDOWN:
🔴/🟡/🟢 Fed      → [stance]
🔴/🟡/🟢 DXY      → {dxy_dir_en} ({dxy_change:+.2f}%)
🔴/🟡/🟢 Yields   → [direction]
🔴/🟡/🟢 Geo Risk → [level]
🔴/🟡/🟢 Oil      → ${oil_price:,.2f}
🔴/🟡/🟢 CFTC     → [signal]

━━━━━━━━━━━━━━━━━━━━━
CFTC DATA (Latest):
Spec longs:  [number]
Spec shorts: [number]
Net:         [number] [arrow]
Signal: [plain English]

━━━━━━━━━━━━━━━━━━━━━
KEY LEVELS:
Support:    $[level] (break = danger)
Resistance: $[level] (bulls need this)

THIS WEEK WATCH:
⚠️ [Date] — [Event] [HIGH/medium impact]
   Hot reading → Gold [prediction]
   Weak reading → Gold [prediction]

━━━━━━━━━━━━━━━━━━━━━
JPM year-end target: $6,000/oz 🎯"""

    return ask_groq(prompt)

# ─────────────────────────────────────────
#  COT BRIEF
# ─────────────────────────────────────────
def generate_cot_brief(language: str) -> str:
    today = datetime.now(PAKISTAN_TZ).strftime("%d %B %Y")
    if language == "urdu":
        prompt = f"""Aaj {today} hai. CFTC COT report ka latest Gold data Roman Urdu mein do.
Net longs, shorts, open interest, aur Gold ke liye signal. Simple aur clear — Telegram format."""
    else:
        prompt = f"""Today is {today}. Give latest CFTC COT report summary for Gold.
Net longs, shorts, open interest, signal for Gold direction. Simple and clear. Telegram format."""
    return ask_groq(prompt)

# ─────────────────────────────────────────
#  TELEGRAM COMMANDS
# ─────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_chat.id)
    if lang == "urdu":
        msg = """🤖 Gold Analysis Bot mein khush aamdeed!

📋 COMMANDS:
/gold    — Abhi Gold brief lo (LIVE prices)
/prices  — Sirf live prices dekho
/week    — Is hafte ka outlook
/cot     — CFTC/COT hedge fund data
/urdu    — Roman Urdu mein switch
/english — English mein switch
/translate — Last brief translate karo
/help    — Madad

🕗 Har Monday 8am Pakistan time — auto brief! 🇵🇰"""
    else:
        msg = """🤖 Welcome to Gold Analysis Bot!

📋 COMMANDS:
/gold    — Get Gold brief (LIVE prices)
/prices  — Live prices only
/week    — This week's outlook
/cot     — CFTC/COT hedge fund data
/urdu    — Switch to Roman Urdu
/english — Switch to English
/translate — Translate last brief
/help    — Help

🕗 Auto brief every Monday 8am Pakistan time! 🇵🇰"""
    await update.message.reply_text(msg)


async def prices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_chat.id)
    wait = "⏳ Live prices la raha hoon..." if lang == "urdu" else "⏳ Fetching live prices..."
    sent = await update.message.reply_text(wait)
    try:
        prices = get_live_prices()
        header = "📊 LIVE MARKET PRICES\n━━━━━━━━━━━━━━━━━━━━━\n" if lang == "english" else "📊 LIVE QEEMTAIN\n━━━━━━━━━━━━━━━━━━━━━\n"
        now = datetime.now(PAKISTAN_TZ).strftime("%d %b %Y, %I:%M %p")
        footer = f"\n━━━━━━━━━━━━━━━━━━━━━\n🕐 {now} (Pakistan)"
        await sent.edit_text(header + format_prices(prices) + footer)
    except Exception as e:
        await sent.edit_text(f"Error: {str(e)}")


async def gold_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)
    wait = "⏳ Live prices + analysis tayyar ho rahi hai..." if lang == "urdu" else "⏳ Fetching live prices + generating analysis..."
    sent = await update.message.reply_text(wait)
    try:
        prices = get_live_prices()
        brief  = generate_gold_brief(lang, prices)
        await sent.delete()
        await update.message.reply_text(brief)
    except Exception as e:
        await sent.edit_text(f"Error: {str(e)}")


async def week_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await gold_command(update, context)


async def cot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)
    wait = "⏳ CFTC data la raha hoon..." if lang == "urdu" else "⏳ Fetching CFTC data..."
    sent = await update.message.reply_text(wait)
    try:
        brief = generate_cot_brief(lang)
        await sent.delete()
        await update.message.reply_text(brief)
    except Exception as e:
        await sent.edit_text(f"Error: {str(e)}")


async def urdu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_language[update.effective_chat.id] = "urdu"
    await update.message.reply_text("✅ Ho gaya! Ab sab Roman Urdu mein aayega.\n\n/gold likh ke try karo! 🇵🇰")


async def english_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_language[update.effective_chat.id] = "english"
    await update.message.reply_text("✅ Switched to English! Type /gold to try.")


async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    current = get_lang(chat_id)
    target  = "urdu" if current == "english" else "english"
    wait = "⏳ Translate ho raha hai..." if current == "english" else "⏳ Translating..."
    sent = await update.message.reply_text(wait)
    try:
        prices = get_live_prices()
        brief  = generate_gold_brief(target, prices)
        await sent.delete()
        await update.message.reply_text(brief)
    except Exception as e:
        await sent.edit_text(f"Error: {str(e)}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_chat.id)
    if lang == "urdu":
        msg = """📖 MADAD

/gold     — Live prices + Gold analysis
/prices   — Sirf live prices
/week     — Hafta wari outlook
/cot      — CFTC hedge fund data
/urdu     — Roman Urdu mein switch
/english  — English mein switch
/translate — Brief translate karo

🕗 Auto brief: Har Monday 8am Pakistan

📊 Live data:
• Gold XAU/USD (real-time)
• Silver XAG/USD
• DXY Dollar Index
• Oil WTI
• EUR/USD, GBP/USD"""
    else:
        msg = """📖 HELP

/gold     — Live prices + Gold analysis
/prices   — Live prices only
/week     — Weekly outlook
/cot      — CFTC hedge fund data
/urdu     — Switch to Roman Urdu
/english  — Switch to English
/translate — Translate brief

🕗 Auto brief: Every Monday 8am Pakistan

📊 Live data included:
• Gold XAU/USD (real-time)
• Silver XAG/USD
• DXY Dollar Index
• Oil WTI
• EUR/USD, GBP/USD"""
    await update.message.reply_text(msg)


# ─────────────────────────────────────────
#  AUTO MONDAY BRIEF
# ─────────────────────────────────────────
async def auto_monday_brief(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(PAKISTAN_TZ)
    if now.weekday() != 0:
        return
    lang = get_lang(YOUR_CHAT_ID)
    try:
        prices = get_live_prices()
        brief  = generate_gold_brief(lang, prices)
        header = "🔔 Hafta wari automatic brief!\n\n" if lang == "urdu" else "🔔 Your weekly auto brief!\n\n"
        await context.bot.send_message(chat_id=YOUR_CHAT_ID, text=header + brief)
    except Exception as e:
        await context.bot.send_message(chat_id=YOUR_CHAT_ID, text=f"Auto brief error: {str(e)}")


# ─────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────
def main():
    logging.basicConfig(level=logging.INFO)
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start",     start))
    app.add_handler(CommandHandler("gold",      gold_command))
    app.add_handler(CommandHandler("prices",    prices_command))
    app.add_handler(CommandHandler("week",      week_command))
    app.add_handler(CommandHandler("cot",       cot_command))
    app.add_handler(CommandHandler("urdu",      urdu_command))
    app.add_handler(CommandHandler("english",   english_command))
    app.add_handler(CommandHandler("translate", translate_command))
    app.add_handler(CommandHandler("help",      help_command))

    app.job_queue.run_daily(
        auto_monday_brief,
        time=datetime.strptime("03:00", "%H:%M").time(),
        days=(0,),
    )

    print("✅ Gold Bot with LIVE prices is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
        
