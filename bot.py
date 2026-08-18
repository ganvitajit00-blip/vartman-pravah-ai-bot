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

# =====================================================
# RENDER WEB SERVER
# =====================================================

server = Flask(__name__)

@server.route("/")
def home():
    return "Vartman Pravah AI Bot is Live! ✅"


def run_web():
    port = int(os.environ.get("PORT", 8080))
    server.run(host="0.0.0.0", port=port)


# =====================================================
# ENVIRONMENT VARIABLES
# =====================================================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing")


# =====================================================
# GEMINI CLIENT
# =====================================================

client = genai.Client(api_key=GEMINI_API_KEY)


# =====================================================
# LOGGING
# =====================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


# =====================================================
# START
# =====================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = (
        "નમસ્તે! 👋\n\n"
        "🇮🇳 વર્તમાન પ્રવાહ AI Bot માં આપનું સ્વાગત છે.\n\n"
        "હવે તમે મને Current Affairs, General Knowledge "
        "અથવા કોઈપણ સામાન્ય પ્રશ્ન પૂછી શકો છો.\n\n"
        "ઉદાહરણ:\n"
        "• આજના Current Affairs આપો\n"
        "• ગુજરાતના આજના સમાચાર આપો\n"
        "• ભારતના મહત્વના સમાચાર આપો\n"
        "• RBIના તાજેતરના સમાચાર આપો\n"
        "• GPSC માટે Current Affairs આપો\n\n"
        "📚 પરીક્ષાર્થીઓ માટે સરળ ગુજરાતીમાં જવાબ મળશે."
    )

    await update.message.reply_text(message)


# =====================================================
# HELP
# =====================================================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = (
        "📚 મદદ\n\n"
        "તમે સીધો પ્રશ્ન મોકલી શકો છો.\n\n"
        "ઉદાહરણ:\n"
        "👉 આજના 10 Current Affairs આપો\n"
        "👉 ગુજરાતના આજના મહત્વના સમાચાર આપો\n"
        "👉 UPSC માટે આજના Current Affairs આપો\n"
        "👉 GPSC માટે 10 MCQ આપો\n"
        "👉 ભારતના રાષ્ટ્રીય સમાચાર આપો\n"
    )

    await update.message.reply_text(message)


# =====================================================
# AI RESPONSE
# =====================================================

async def answer_question(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    question = update.message.text.strip()

    if not question:
        return

    loading = await update.message.reply_text(
        "🔎 જવાબ તૈયાર કરી રહ્યો છું... થોડી ક્ષણ રાહ જુઓ."
    )

    try:

        system_prompt = """
તમે 'વર્તમાન પ્રવાહ' નામના ગુજરાતી Current Affairs
અને General Knowledge AI Bot છો.

તમારું કામ પરીક્ષાર્થીઓને ઉપયોગી થાય તે રીતે
સરળ, સ્પષ્ટ અને મુદ્દાસર ગુજરાતીમાં જવાબ આપવાનું છે.

જવાબ આપતી વખતે:

1. ગુજરાતીમાં જવાબ આપો.
2. જરૂરી હોય ત્યાં મુદ્દાવાર માહિતી આપો.
3. Current Affairs માટે તારીખ સ્પષ્ટ લખો.
4. જો માહિતી ચોક્કસ ન હોય તો ખોટી માહિતી ન બનાવો.
5. પરીક્ષાર્થીઓ માટે મહત્વના facts અલગથી દર્શાવો.
6. જરૂરી હોય ત્યારે MCQ પણ બનાવી શકો છો.
"""

        prompt = (
            system_prompt
            + "\n\nયુઝરનો પ્રશ્ન:\n"
            + question
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt
        )

        answer = response.text

        if not answer:
            answer = "માફ કરશો, હાલમાં જવાબ મેળવી શકાયો નથી."

        # Telegram message limit
        max_length = 4000

        if len(answer) <= max_length:

            await loading.edit_text(answer)

        else:

            await loading.edit_text(
                answer[:max_length]
            )

            remaining = answer[max_length:]

            while remaining:

                chunk = remaining[:4000]
                remaining = remaining[4000:]

                await update.message.reply_text(chunk)

    except Exception as e:

        logging.exception(
            "Gemini API Error"
        )

        error_message = (
            "❌ AI જવાબ આપવામાં સમસ્યા આવી.\n\n"
            "થોડીવાર પછી ફરી પ્રયાસ કરો."
        )

        await loading.edit_text(error_message)


# =====================================================
# ERROR HANDLER
# =====================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logging.error(
        "Exception while handling update:",
        exc_info=context.error
    )


# =====================================================
# MAIN
# =====================================================

def main():

    # Start Render web server
    Thread(
        target=run_web,
        daemon=True
    ).start()

    # Telegram application
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    # Commands
    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("help", help_command)
    )

    # Normal messages
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            answer_question
        )
    )

    # Error handler
    application.add_error_handler(
        error_handler
    )

    print(
        "🇮🇳 Vartman Pravah AI Bot is running..."
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


# =====================================================
# START BOT
# =====================================================

if __name__ == "__main__":
    main()
