import os
import json
import asyncio
import logging
from datetime import datetime
from groq import Groq
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, JobQueue
import pytz

# ─────────────────────────────────────────
#  CONFIG — APNI KEYS YAHAN DAAL
# ─────────────────────────────────────────
TELEGRAM_TOKEN = "8651506670:AAGCEH2OyL0RazZ3pSaWtNSZ_EPPZpEKLFU"
GROQ_API_KEY   = "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"
YOUR_CHAT_ID   =  7028226344

PAKISTAN_TZ = pytz.timezone("Asia/Karachi")

# ─────────────────────────────────────────
#  USER LANGUAGE SETTINGS
# ─────────────────────────────────────────
user_language = {}  # chat_id -> "urdu" or "english"

def get_lang(chat_id):
    return user_language.get(chat_id, "english")

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
def generate_gold_brief(language: str) -> str:
    today = datetime.now(PAKISTAN_TZ).strftime("%A, %d %B %Y")

    if language == "urdu":
        prompt = f"""Tu ek professional Gold market analyst hai. Aaj ki date hai {today}.

Mujhe Gold (XAU/USD) ka weekly analysis chahiye Roman Urdu mein — jaise ek dost samjha raha ho.

Yeh information include karo:
1. Gold ki current approximate price aur weekly performance
2. US Dollar (DXY) ka rukh — upar ja raha hai ya neeche
3. Federal Reserve ka stance — hawkish hai ya dovish (Urdu mein samjhao)
4. Geopolitical risk — duniya mein kya chal raha hai jo Gold ko affect kare
5. CFTC/COT data — bade hedge funds kya kar rahe hain Gold ke saath
6. Real yields — US bonds ka munafa Gold ko kaise affect kar raha hai
7. Oil prices — tel ki qeemat ka Gold pe asar

Phir yeh do:
- BEARISH, BULLISH ya NEUTRAL — ek word mein verdict
- Score 0-100 (0 = zyada bearish, 100 = zyada bullish)
- 4-5 short reasons WHY (har reason ek line mein, simple Urdu mein)
- Har factor ke liye 🔴 (bearish) 🟡 (neutral) 🟢 (bullish) signal
- Support aur resistance levels
- Is hafte ke important economic events
- Kya watch karna chahiye

Format bilkul aisa rakho (Telegram ke liye):

📊 GOLD HAFTA WARI BRIEF — {today}
━━━━━━━━━━━━━━━━━━━━━

📍 Qeemat: $[price] | Weekly: [%]
📊 Rukh: [VERDICT] | Score: [X]/100
💡 Asli wajah: [one line main driver]

KYUN [VERDICT]:
→ [reason 1 - simple Urdu mein]
→ [reason 2]
→ [reason 3]
→ [reason 4]
→ [reason 5]

━━━━━━━━━━━━━━━━━━━━━
FACTOR CHECK:
🔴/🟡/🟢 Fed       → [stance - Urdu]
🔴/🟡/🟢 Dollar    → [direction - Urdu]
🔴/🟡/🟢 Yields    → [direction - Urdu]
🔴/🟡/🟢 Geo Risk  → [level - Urdu]
🔴/🟡/🟢 Tel       → [direction - Urdu]
🔴/🟡/🟢 CFTC      → [signal - Urdu]

━━━━━━━━━━━━━━━━━━━━━
CFTC DATA (Latest):
Spec longs:  [number]
Spec shorts: [number]
Net:         [number] [direction]
Signal: [plain Urdu mein kya matlab]

━━━━━━━━━━━━━━━━━━━━━
KEY LEVELS:
Support:    $[level] ([Urdu note])
Resistance: $[level] ([Urdu note])

IS HAFTE WATCH KARO:
⚠️ [Date] — [Event] [impact level]
   Agar zyada → Gold [prediction]
   Agar kam   → Gold [prediction]

━━━━━━━━━━━━━━━━━━━━━
JPM saal ke aakhir target: $6,000/oz 🎯"""

    else:
        prompt = f"""You are a professional Gold market analyst. Today is {today}.

Give me a complete Gold (XAU/USD) weekly analysis brief for a beginner trader.

Cover:
1. Gold current approximate price and weekly performance
2. US Dollar Index (DXY) direction
3. Federal Reserve stance — hawkish or dovish with brief reason
4. Geopolitical risk affecting Gold
5. CFTC/COT positioning — what are hedge funds doing
6. Real yields direction and impact on Gold
7. Oil prices impact

Then provide:
- One word verdict: BEARISH, BULLISH or NEUTRAL
- Bias score 0-100
- 4-5 short one-line reasons WHY
- Factor signals with emoji
- Support and resistance levels
- Key events this week with scenarios

Format exactly like this for Telegram:

📊 GOLD WEEKLY BRIEF — {today}
━━━━━━━━━━━━━━━━━━━━━

📍 Spot: $[price] | Weekly: [%]
📊 Bias: [VERDICT] | Score: [X]/100
💡 Main driver: [one line]

WHY [VERDICT]:
→ [reason 1 - simple and clear]
→ [reason 2]
→ [reason 3]
→ [reason 4]
→ [reason 5]

━━━━━━━━━━━━━━━━━━━━━
FACTOR BREAKDOWN:
🔴/🟡/🟢 Fed      → [stance]
🔴/🟡/🟢 DXY      → [direction]
🔴/🟡/🟢 Yields   → [direction]
🔴/🟡/🟢 Geo Risk → [level]
🔴/🟡/🟢 Oil      → [direction]
🔴/🟡/🟢 CFTC     → [signal]

━━━━━━━━━━━━━━━━━━━━━
CFTC DATA (Latest):
Spec longs:  [number]
Spec shorts: [number]
Net:         [number] [arrow]
Signal: [plain English explanation]

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
#  COT BRIEF GENERATOR
# ─────────────────────────────────────────
def generate_cot_brief(language: str) -> str:
    today = datetime.now(PAKISTAN_TZ).strftime("%d %B %Y")
    if language == "urdu":
        prompt = f"""Aaj {today} hai. Mujhe CFTC COT report ka latest Gold data chahiye Roman Urdu mein.

Yeh include karo:
- Non-commercial (hedge funds) net longs — kitne hain aur gaye hafte se zyada ya kam
- Shorts growing hain ya nahi
- Open interest
- Iska kya matlab hai Gold ke liye — bearish hai ya bullish

Simple rakho — jaise dost samjha raha ho. Telegram format mein."""
    else:
        prompt = f"""Today is {today}. Give me the latest CFTC COT report summary for Gold.

Include:
- Non-commercial net longs — current number and change from last week
- Are shorts growing or falling
- Open interest change
- What this means for Gold direction — bullish or bearish signal

Keep it simple and clear. Telegram format."""

    return ask_groq(prompt)


# ─────────────────────────────────────────
#  TELEGRAM COMMANDS
# ─────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_chat.id)
    if lang == "urdu":
        msg = """🤖 Gold Analysis Bot mein khush aamdeed!

📋 COMMANDS:
/gold — Abhi Gold brief lo
/week — Is hafte ka outlook
/cot  — CFTC/COT data
/urdu — Roman Urdu mein switch karo
/english — English mein switch karo
/translate — Last brief translate karo
/help — Madad

Har Monday 8am Pakistan time — automatic brief aata hai! 🇵🇰"""
    else:
        msg = """🤖 Welcome to Gold Analysis Bot!

📋 COMMANDS:
/gold — Get Gold brief now
/week — This week's outlook
/cot  — CFTC/COT positioning data
/urdu — Switch to Roman Urdu
/english — Switch to English
/translate — Translate last brief
/help — Help

Auto brief every Monday 8am Pakistan time! 🇵🇰"""
    await update.message.reply_text(msg)


async def gold_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)
    wait_msg = "⏳ Analyzing Gold markets... thoda wait karo..." if lang == "urdu" else "⏳ Analyzing Gold markets... please wait..."
    sent = await update.message.reply_text(wait_msg)
    try:
        brief = generate_gold_brief(lang)
        await sent.delete()
        await update.message.reply_text(brief)
    except Exception as e:
        await sent.edit_text(f"Error: {str(e)}\nThodi der baad try karo.")


async def week_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await gold_command(update, context)


async def cot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang = get_lang(chat_id)
    wait_msg = "⏳ CFTC data la raha hoon..." if lang == "urdu" else "⏳ Fetching CFTC data..."
    sent = await update.message.reply_text(wait_msg)
    try:
        brief = generate_cot_brief(lang)
        await sent.delete()
        await update.message.reply_text(brief)
    except Exception as e:
        await sent.edit_text(f"Error: {str(e)}")


async def urdu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_language[chat_id] = "urdu"
    await update.message.reply_text("✅ Theek hai! Ab sab kuch Roman Urdu mein aayega.\n\n/gold likh ke try karo!")


async def english_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_language[chat_id] = "english"
    await update.message.reply_text("✅ Switched to English! Type /gold to try.")


async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    current = get_lang(chat_id)
    target = "urdu" if current == "english" else "english"
    wait_msg = "⏳ Translate ho raha hai..." if current == "english" else "⏳ Translating..."
    sent = await update.message.reply_text(wait_msg)
    try:
        brief = generate_gold_brief(target)
        await sent.delete()
        await update.message.reply_text(brief)
    except Exception as e:
        await sent.edit_text(f"Error: {str(e)}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_chat.id)
    if lang == "urdu":
        msg = """📖 MADAD / HELP

/gold     — Abhi Gold analysis lo
/week     — Hafta wari outlook
/cot      — CFTC hedge fund data
/urdu     — Roman Urdu mein switch
/english  — English mein switch
/translate — Brief translate karo

🕗 Auto brief: Har Monday 8am (Pakistan)

📊 Data jo bot cover karta hai:
• Gold spot price
• DXY (Dollar strength)
• Fed stance (hawkish/dovish)
• Real yields
• Geopolitical risk
• CFTC/COT positioning
• Oil prices
• Key economic events"""
    else:
        msg = """📖 HELP

/gold     — Get Gold analysis now
/week     — Weekly outlook
/cot      — CFTC hedge fund positioning
/urdu     — Switch to Roman Urdu
/english  — Switch to English
/translate — Translate last brief

🕗 Auto brief: Every Monday 8am (Pakistan)

📊 Data covered:
• Gold spot price & weekly performance
• DXY (Dollar Index)
• Fed stance
• Real yields
• Geopolitical risk
• CFTC/COT positioning
• Oil prices
• Key economic events"""
    await update.message.reply_text(msg)


# ─────────────────────────────────────────
#  AUTO MONDAY BRIEF — SCHEDULED JOB
# ─────────────────────────────────────────
async def auto_monday_brief(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(PAKISTAN_TZ)
    if now.weekday() != 0:  # 0 = Monday
        return
    lang = get_lang(YOUR_CHAT_ID)
    try:
        brief = generate_gold_brief(lang)
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
    app.add_handler(CommandHandler("week",      week_command))
    app.add_handler(CommandHandler("cot",       cot_command))
    app.add_handler(CommandHandler("urdu",      urdu_command))
    app.add_handler(CommandHandler("english",   english_command))
    app.add_handler(CommandHandler("translate", translate_command))
    app.add_handler(CommandHandler("help",      help_command))

    # Every Monday at 8:00am Pakistan time = 3:00am UTC
    app.job_queue.run_daily(
        auto_monday_brief,
        time=datetime.strptime("03:00", "%H:%M").time(),
        days=(0,),  # Monday only
    )

    print("✅ Gold Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
