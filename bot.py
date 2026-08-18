import os
import logging
from threading import Thread
from flask import Flask
from google import genai
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# -----------------------------
# KEEP-ALIVE WEB SERVER FOR RENDER
# -----------------------------
server = Flask(__name__)

@server.route('/')
def home():
    return "Bot is Live and Running!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    server.run(host="0.0.0.0", port=port)

# -----------------------------
# SETTINGS & KEYS
# -----------------------------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing")

client = genai.Client(api_key=GEMINI_API_KEY)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# -----------------------------
# START COMMAND
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "નમસ્તે! 🙏\n\n"
        "વર્તમાન પ્રવાહ AI Bot માં આપનું સ્વાગત છે. 🤖\n\n"
        "તમે ગુજરાતીમાં કોઈપણ પ્રશ્ન પૂછી શકો છો.\n\n"
        "ઉદાહરણ:\n"
        "• ગુજરાતના આજના સમાચાર\n"
        "• આજના 5 મહત્વના સમાચાર\n"
        "• સામાન્ય જ્ઞાનનો પ્રશ્ન\n"
        "• બંધારણ વિશે માહિતી\n"
        "• Current Affairs\n"
        "• પરીક્ષા માટે MCQ\n\n"
        "તમારો પ્રશ્ન મોકલો 👇"
    )
    await update.message.reply_text(message)

# -----------------------------
# AI RESPONSE (GEMINI)
# -----------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = update.message.text.strip()
    if not question:
        return

    loading = await update.message.reply_text("🔎 માહિતી મેળવી રહ્યો છું... થોડી ક્ષણ રાહ જુઓ.")

    try:
        system_instruction = (
            "તમે 'વર્તમાન પ્રવાહ' નામના ગુજરાતી સહાયક છો. "
            "ગુજરાતી ભાષામાં સ્પષ્ટ, સચોટ અને પરીક્ષાલક્ષી જવાબો આપો."
        )

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=question,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_instruction
            )
        )

        answer = response.text if response.text else "માફ કરશો, જવાબ ઉપલબ્ધ નથી."

        # Telegram message size limit handler
        max_length = 4000
        if len(answer) <= max_length:
            await loading.edit_text(answer)
        else:
            await loading.edit_text(answer[:max_length])
            remaining = answer[max_length:]
            while remaining:
                chunk = remaining[:4000]
                remaining = remaining[4000:]
                await update.message.reply_text(chunk)

    except Exception as e:
        logging.exception("Error while processing message")
        await loading.edit_text("❌ હાલમાં AI જવાબ આપવામાં સમસ્યા આવી છે. થોડા સમય પછી ફરી પ્રયાસ કરો.")

# -----------------------------
# MAIN RUNNER
# -----------------------------
def main():
    Thread(target=run_web).start()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Vartman Pravah AI Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
